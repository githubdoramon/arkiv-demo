"""Small, durable demo keeper for permissionless Arkiv entity extensions.

Credits are derived from the current queryable snapshot. SQLite stores consumed
rolling windows and exact target jobs so polling/retries cannot compound them.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)
DAY = 86400
WINDOW = 30
DEFAULT_DAILY_BUDGET_GLM = 0.1


def _payload(entity: dict[str, Any]) -> dict[str, Any]:
    value = entity.get("payload") or {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


def _norm(value: Any) -> str:
    return str(value or "").lower()


class RenewalWorker:
    """Derive credits and optionally submit keeper-paid extensions.

    `rpc_url`, `keeper_key`, and `state_path` configure the SDK connection and
    local idempotency ledger. `sdk_client` and `submitter` are test seams; normal
    live operation uses the sibling Python SDK's ``Arkiv.extend_entity``.
    """

    def __init__(self, rpc_url: str = "http://127.0.0.1:18547", keeper_key: str | None = None,
                 state_path: str | Path = "./runtime/renewal.sqlite3", *,
                 daily_budget_glm: float | None = None,
                 sdk_client: Any = None, submitter: Any = None,
                 games: list[dict[str, Any]] | None = None):
        if daily_budget_glm is None:
            daily_budget_glm = float(os.getenv("ARKIV_RENEWAL_DAILY_BUDGET_GLM", DEFAULT_DAILY_BUDGET_GLM))
        if daily_budget_glm < 0:
            raise ValueError("daily_budget_glm must be nonnegative")
        self.rpc_url, self.keeper_key = rpc_url, keeper_key
        self.state_path = Path(state_path)
        self.daily_budget_glm = float(daily_budget_glm)
        self.sdk_client, self.submitter = sdk_client, submitter
        self.games = games
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS credits(id TEXT PRIMARY KEY, root TEXT NOT NULL,
                  actor TEXT NOT NULL, event_day INTEGER NOT NULL, days REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs(entity TEXT PRIMARY KEY, baseline INTEGER NOT NULL,
                  target INTEGER NOT NULL, credits TEXT NOT NULL, status TEXT NOT NULL,
                  tx_hash TEXT, receipt TEXT, attempts INTEGER NOT NULL DEFAULT 0,
                  retry_after INTEGER NOT NULL DEFAULT 0, last_error TEXT);
                CREATE TABLE IF NOT EXISTS spend(day INTEGER PRIMARY KEY, glm REAL NOT NULL);
            """)

    def _db(self):
        return sqlite3.connect(self.state_path, timeout=10)

    def _credits(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        validated = self._validated(snapshot)
        roots = {_norm(e["key"]): e for e in validated["roots"]}
        revisions = {_norm(e["key"]): e for e in validated["revisions"]}
        root_by_revision = {_norm(revision["key"]): _norm(revision["payload"]["root_key"])
                            for revision in validated["revisions"]}
        nowday = int(snapshot.get("evaluation_day", int(snapshot.get("block_timestamp", 0)) // DAY))
        per_actor_root: dict[tuple[str, str], dict[str, Any]] = {}
        feedback_entities = validated["votes"] + validated["comments"]
        for e in feedback_entities:
            p = e["payload"]
            kind = e["attributes"]["kind"]
            revkey = _norm(p.get("target_revision_key"))
            rev = revisions.get(revkey)
            if rev is None:
                continue
            root_key = root_by_revision[revkey]
            actor = _norm(p.get("voter") if kind == "review-vote" else p.get("author"))
            if root_key not in roots or not actor:
                raise ValueError("Validated feedback references an unexpected actor or root")
            if kind == "review-vote" and p.get("value") != "helpful":
                continue
            root_author = _norm(roots[root_key]["payload"]["author"])
            if actor == root_author:
                continue
            created = int(e["created_at_timestamp"])
            day = created // DAY
            if day > nowday or nowday - day >= WINDOW:
                continue
            # One qualifying action per actor/root while a prior earned credit is
            # still inside the rolling window. Event-key identity is retry-stable.
            k = (root_key, actor)
            event = {"id": f"{root_key}:{actor}:{_norm(e['key'])}", "root": root_key,
                     "actor": actor, "day": day, "weight": 1.0,
                     "evidence_key": _norm(e["key"])}
            existing = per_actor_root.get(k)
            if existing is None or (day, event["evidence_key"]) < (existing["day"], existing["evidence_key"]):
                per_actor_root[k] = event
        # Each participant/root rolling 30-day window yields one 7-day credit.
        # Weight hook may be supplied by core's day-start reputation projection.
        from .reputation import calculate_scores, events_from_entities, voter_weight
        author_by_revision = {_norm(r["key"]): _norm(r["payload"]["author"])
                              for r in validated["revisions"]}
        vote_events = events_from_entities(validated["votes"], author_by_revision)
        for event in per_actor_root.values():
            # Exclude same-day feedback, but decay earlier evidence up to the
            # actual event day so this matches reputation's day-start weights.
            earlier = [vote for vote in vote_events if vote.day < event["day"]]
            scores = calculate_scores(earlier, evaluation_day=event["day"])
            event["weight"] = voter_weight(scores.get(event["actor"], 0.0))
        candidates = []
        with self._db() as db:
            for event in per_actor_root.values():
                recent = db.execute("SELECT 1 FROM credits WHERE root=? AND actor=? AND event_day>? LIMIT 1",
                                    (event["root"], event["actor"], event["day"] - WINDOW)).fetchone()
                if recent:
                    continue
                candidates.append({**event, "days": min(7.0 * max(0.0, event["weight"]), 30.0)})
        # The cap is per root over any trailing 30-day period, not reset by edits.
        by_root: dict[str, list[dict[str, Any]]] = {}
        for item in candidates:
            by_root.setdefault(item["root"], []).append(item)
        output = []
        for root_key, items in by_root.items():
            remaining = 30.0
            with self._db() as db:
                prior = db.execute("SELECT COALESCE(SUM(days),0) FROM credits WHERE root=? AND event_day>?",
                                   (root_key, nowday - WINDOW)).fetchone()[0]
            remaining = max(0.0, remaining - float(prior))
            for item in sorted(items, key=lambda x: (x["day"], x["evidence_key"])):
                earned = min(item["days"], remaining)
                if earned > 0:
                    output.append({**item, "days": earned})
                    remaining -= earned
        return output

    def run_once(self, snapshot: dict[str, Any], dry_run: bool = True) -> dict[str, Any]:
        """Plan/reconcile expiry targets; submitting is always explicit."""
        if not dry_run and not (self.submitter or self.sdk_client or (self.rpc_url and self.keeper_key)):
            raise ValueError("Live renewal requires rpc_url and keeper_key")
        entities = {_norm(e.get("key")): e for e in snapshot.get("entities", [])}
        credits = self._credits(snapshot)
        day = int(snapshot.get("evaluation_day", 0))
        block = int(snapshot.get("block_number", 0))
        # Root and every valid revision receive the same root budget, preserving
        # the visible review chain as one unit. Evidence entities are renewed only
        # where they are themselves canonical eligible records attached to it.
        targets: dict[str, tuple[int, list[str]]] = {}

        def extension_eligible(entity: dict[str, Any]) -> bool:
            flags = entity.get("flags") or {}
            attrs = entity.get("attributes") or {}
            return (attrs.get("app") == "arkiv-review-demo"
                    and flags.get("readonly") is True
                    and flags.get("permissionless_extension") is True)

        canonical = self._validated(snapshot)
        canonical_revisions = {_norm(e["key"]): e for e in canonical["revisions"]}
        canonical_feedback = canonical["votes"] + canonical["comments"]
        revision_to_root = {_norm(e["key"]): _norm(e["payload"]["root_key"])
                            for e in canonical["revisions"]}
        for root in credits:
            rootkey = root["root"]
            related = [rootkey]
            related += [k for k in canonical_revisions if revision_to_root.get(k) == rootkey]
            for evidence in canonical_feedback:
                target_revision = _norm(_payload(evidence).get("target_revision_key"))
                if revision_to_root.get(target_revision) == rootkey:
                    related.append(_norm(evidence.get("key")))
            for key in related:
                if key not in entities or not extension_eligible(entities[key]):
                    continue
                prev = targets.setdefault(key, (int(entities[key].get("expires_at_block", 0)), []))
                if root["id"] not in prev[1]:
                    prev[1].append(root["id"])
        # Continue retry/reconciliation work even when all qualifying evidence
        # was consumed on a previous invocation.
        with self._db() as db:
            for key, baseline, saved_target, saved_ids, status in db.execute(
                    "SELECT entity,baseline,target,credits,status FROM jobs WHERE status!='complete'"):
                if key in entities and extension_eligible(entities[key]):
                    targets.setdefault(key, (int(baseline), list(json.loads(saved_ids))))
        rows = []
        with self._db() as db:
            if not dry_run:
                for credit in credits:
                    db.execute("INSERT OR IGNORE INTO credits VALUES(?,?,?,?,?)",
                               (credit["id"], credit["root"], credit["actor"], credit["day"], credit["days"]))
            new_credit_days = {credit["id"]: credit["days"] for credit in credits}
            for key, (baseline, ids) in targets.items():
                if baseline <= block:
                    rows.append({"entity_key": key, "status": "expired", "target_expiry_block": None})
                    continue
                saved_credit_days = dict(db.execute("SELECT id,days FROM credits WHERE id IN (%s)" %
                                                     (','.join('?' * len(ids)) or "NULL"), ids).fetchall())
                applied = sum(float(saved_credit_days.get(credit_id, new_credit_days.get(credit_id, 0.0)))
                              for credit_id in ids)
                target = baseline + int(applied * DAY / 2)  # nominal two-second blocks
                job = db.execute("SELECT target,credits,status,tx_hash,receipt FROM jobs WHERE entity=?", (key,)).fetchone()
                if job:
                    computed_target = target
                    ids = sorted(set(ids) | set(json.loads(job[1])))
                    if int(job[0]) >= computed_target:
                        target = int(job[0])
                    else:
                        target = computed_target
                if target <= baseline:
                    rows.append({"entity_key": key, "status": "no-op", "target_expiry_block": baseline})
                    continue
                if job and job[2] == "complete" and int(job[0]) >= target:
                    rows.append({"entity_key": key, "status": "complete", "target_expiry_block": target,
                                 "tx_hash": job[3], "receipt": json.loads(job[4]) if job[4] else None})
                    continue
                db.execute("INSERT INTO jobs(entity,baseline,target,credits,status) VALUES(?,?,?,?,?) "
                           "ON CONFLICT(entity) DO UPDATE SET target=MAX(target,excluded.target),credits=excluded.credits",
                           (key, baseline, target, json.dumps(ids), "planned"))
                if dry_run:
                    rows.append({"entity_key": key, "status": "dry-run", "target_expiry_block": target,
                                 "credit_ids": ids})
                    continue
                jobrow = db.execute("SELECT retry_after,attempts FROM jobs WHERE entity=?", (key,)).fetchone()
                if int(jobrow[0]) > int(time.time()):
                    rows.append({"entity_key": key, "status": "backoff", "target_expiry_block": target})
                    continue
                spent = db.execute("SELECT glm FROM spend WHERE day=?", (day,)).fetchone()
                if self.daily_budget_glm == 0 or (spent and spent[0] >= self.daily_budget_glm):
                    rows.append({"entity_key": key, "status": "budget-exhausted", "target_expiry_block": target})
                    continue
                try:
                    current_expiry = self._current_expiry(key, entities[key])
                    if current_expiry is None or current_expiry <= block:
                        rows.append({"entity_key": key, "status": "expired", "target_expiry_block": target})
                        continue
                    if current_expiry >= target:
                        db.execute("UPDATE jobs SET status='complete' WHERE entity=?", (key,))
                        rows.append({"entity_key": key, "status": "complete", "target_expiry_block": target,
                                     "reconciled": True})
                        continue
                    result = self._extend(key, target)
                    receipt = result.get("receipt") if isinstance(result, dict) else getattr(result, "receipt", None)
                    tx = result.get("tx_hash") if isinstance(result, dict) else getattr(result, "tx_hash", None)
                    # SDK returns only after mined receipt; expiry comes from decoded event/result.
                    expiry = result.get("expires_at") if isinstance(result, dict) else getattr(result, "expires_at", None)
                    if expiry is None and isinstance(result, dict):
                        expiry = result.get("expires_at")
                    if expiry is None or int(expiry) < target:
                        raise RuntimeError("extension receipt did not confirm the requested absolute expiry")
                    encoded_receipt = json.dumps(receipt, default=str) if receipt is not None else None
                    db.execute("UPDATE jobs SET status='complete',tx_hash=?,receipt=?,attempts=attempts+1 WHERE entity=?",
                               (tx, encoded_receipt, key))
                    # Gas cost is measured from receipt when available; fallback is conservative no-submit.
                    cost = self._receipt_glm(receipt)
                    db.execute("INSERT INTO spend(day,glm) VALUES(?,?) ON CONFLICT(day) DO UPDATE SET glm=glm+excluded.glm",
                               (day, cost))
                    rows.append({"entity_key": key, "status": "complete", "target_expiry_block": target,
                                 "tx_hash": tx, "receipt": receipt})
                except Exception as exc:
                    attempts = int(jobrow[1]) + 1
                    db.execute("UPDATE jobs SET status='retryable',attempts=?,retry_after=?,last_error=? WHERE entity=?",
                               (attempts, int(time.time()) + min(3600, 2 ** min(attempts, 10)), str(exc)[:300], key))
                    log.warning("renewal failed for %s: %s", key, exc)
                    rows.append({"entity_key": key, "status": "retryable", "target_expiry_block": target,
                                 "error": str(exc)[:200]})
        return {"dry_run": bool(dry_run), "evaluation_day": day, "daily_budget_glm": self.daily_budget_glm,
                "targets": rows, "credit_count": len(credits)}

    def _extend(self, key: str, target: int):
        if self.submitter:
            return self.submitter(key, target)
        client = self.sdk_client
        close = False
        if client is None:
            from arkiv import Arkiv, ExpirationTime
            client = Arkiv(self.rpc_url, account=self.keeper_key)
            close = True
        try:
            from arkiv import ExpirationTime
            # Absolute deadline is essential: relative lifetime would reset from now.
            result = client.extend_entity(key, ExpirationTime.at_block(target))
            receipt = client.eth.get_transaction_receipt(result.tx_hash)
            return {"entity_key": key, "tx_hash": result.tx_hash,
                    "expires_at": result.expires_at, "receipt": dict(receipt)}
        finally:
            if close:
                client.close()

    def _validated(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        from .domain import validate_snapshot
        catalog_path = Path(os.environ.get("ARKIV_CATALOG_PATH", str(Path(__file__).resolve().parents[3] / "shared" / "games.json")))
        if self.games is None and not catalog_path.exists():
            raise RuntimeError(f"Renewal requires the shared game catalog at {catalog_path}")
        games = self.games if self.games is not None else json.loads(catalog_path.read_text())
        validated = validate_snapshot(snapshot, games)
        if not isinstance(validated, dict):
            raise RuntimeError("Core snapshot validation returned an invalid result")
        return validated

    def _current_expiry(self, key: str, snapshot_entity: dict[str, Any]) -> int | None:
        if self.submitter:
            # The injected submitter is responsible for making its own fresh read.
            return int(snapshot_entity.get("expires_at_block", 0))
        client = self.sdk_client
        close = False
        if client is None:
            from arkiv import Arkiv
            client = Arkiv(self.rpc_url, account=self.keeper_key)
            close = True
        try:
            return int(client.get_entity(key).expires_at)
        except Exception:
            return None
        finally:
            if close:
                client.close()

    def _receipt_glm(self, receipt: Any) -> float:
        # Arkiv test-chain gas accounting is denominated in the chain's GLM-like
        # native unit. Unknown receipt costs consume the full ceiling fail-closed.
        if not isinstance(receipt, dict):
            return self.daily_budget_glm
        try:
            gas = receipt["gasUsed"]
            price = receipt["effectiveGasPrice"]
            gas = gas if isinstance(gas, int) else int(str(gas), 0)
            price = price if isinstance(price, int) else int(str(price), 0)
            return gas * price / 10**18
        except (KeyError, TypeError, ValueError):
            return self.daily_budget_glm
