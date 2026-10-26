from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

from arkiv_reviews.renewal import RenewalWorker

AUTHOR = "0x" + "11" * 20
ACTOR = "0x" + "22" * 20
OTHER = "0x" + "33" * 20
ROOT = "0x" + "aa" * 32
REV = "0x" + "bb" * 32
DAY = 20_752


def entity(key, creator, kind, payload, attrs, *, created=1_793_016_000, expiry=8_000_000):
    return {"key": key, "creator": creator, "owner": creator, "created_at_block": 10,
            "created_at_timestamp": created, "expires_at_block": expiry,
            "flags": {"readonly": True, "permissionless_extension": True},
            "attributes": {"app": "arkiv-review-demo", "kind": kind, **attrs}, "payload": payload}


def snapshot(feedback):
    root_payload = {"schema": "review-root/v1", "author": AUTHOR, "game_id": "game-a",
                    "platform": "pc", "logical_id": f"review:1337:{AUTHOR}:game-a:pc"}
    rev_payload = {"schema": "review-revision/v1", "root_key": ROOT, "revision": 1,
                   "previous_revision_key": None, "rating_half_stars": 8, "text": "Solid game",
                   "author": AUTHOR, "logical_id": f"{ROOT}:revision:1"}
    root = entity(ROOT, AUTHOR, "review-root", root_payload,
                  {"author": AUTHOR, "game_id": "game-a", "platform": "pc",
                   "logical_id": root_payload["logical_id"]})
    rev = entity(REV, AUTHOR, "review-revision", rev_payload,
                 {"root_key": ROOT, "revision": 1, "logical_id": rev_payload["logical_id"]})
    return {"chain_id": 1337, "block_number": 1000, "block_timestamp": DAY * 86400,
            "evaluation_day": DAY, "entities": [root, rev, *feedback]}


def vote(key, creator, voter, value):
    payload = {"schema": "review-vote/v1", "target_revision_key": REV, "voter": voter,
               "value": value, "logical_id": f"vote:{REV}:{voter}"}
    return entity(key, creator, "review-vote", payload,
                  {"target_revision_key": REV, "voter": voter, "logical_id": payload["logical_id"]})


def comment(key, actor, created=DAY * 86400):
    payload = {"schema": "review-comment/v1", "target_revision_key": REV, "author": actor,
               "text": "Useful note", "logical_id": f"comment:{uuid.uuid5(uuid.NAMESPACE_URL, key)}"}
    return entity(key, actor, "review-comment", payload,
                  {"target_revision_key": REV, "author": actor, "logical_id": payload["logical_id"]},
                  created=created)


def games():
    return [{"id": "game-a", "platforms": ["pc"]}]


def test_helpful_or_first_comment_credits_once_but_self_and_unhelpful_do_not(tmp_path):
    data = snapshot([
        vote("0x" + "c1" * 32, AUTHOR, AUTHOR, "helpful"),
        vote("0x" + "c2" * 32, OTHER, OTHER, "unhelpful"),
        comment("0x" + "d1" * 32, ACTOR),
        comment("0x" + "d2" * 32, ACTOR, DAY * 86400 + 10),
    ])
    worker = RenewalWorker(state_path=tmp_path / "renew.sqlite", games=games())
    credits = worker._credits(data)
    assert len(credits) == 1
    assert credits[0]["actor"] == ACTOR
    assert abs(credits[0]["days"] - 0.007) < 1e-9  # fresh wallet has 0.001 weight


def test_validation_and_extension_flags_gate_credits_and_targets(tmp_path):
    feedback = comment("0x" + "d1" * 32, ACTOR)
    feedback["flags"]["permissionless_extension"] = False
    data = snapshot([feedback])
    worker = RenewalWorker(state_path=tmp_path / "renew.sqlite", games=games())
    assert worker._credits(data) == []
    assert worker.run_once(data)["targets"] == []


def test_unknown_receipt_cost_consumes_the_configured_ceiling(tmp_path):
    worker = RenewalWorker(state_path=tmp_path / "renew.sqlite", daily_budget_glm=0.5, games=games())
    assert worker._receipt_glm(None) == 0.5


def test_dry_run_is_idempotent_and_records_durable_stable_target(tmp_path):
    data = snapshot([comment("0x" + "d1" * 32, ACTOR)])
    submit = lambda key, target: {"expires_at": target, "tx_hash": "0xabc",
                                  "receipt": {"gasUsed": "0x1", "effectiveGasPrice": "0x1"}}
    worker = RenewalWorker(state_path=tmp_path / "renew.sqlite", games=games(), submitter=submit)
    first = worker.run_once(data)
    second = worker.run_once(data)
    assert first["credit_count"] == 1
    assert second["credit_count"] == 1
    assert {row["target_expiry_block"] for row in first["targets"]} == {
        row["target_expiry_block"] for row in second["targets"]
    }
    with worker._db() as db:
        assert db.execute("SELECT COUNT(*) FROM credits").fetchone()[0] == 0
    live = worker.run_once(data, dry_run=False)
    assert all(row["status"] == "complete" for row in live["targets"])
    with worker._db() as db:
        assert db.execute("SELECT COUNT(*) FROM credits").fetchone()[0] == 1


def test_retry_uses_same_target_and_does_not_resubmit_after_receipt(tmp_path):
    data = snapshot([comment("0x" + "d1" * 32, ACTOR)])
    calls = []

    def submit(key, target):
        calls.append((key, target))
        return SimpleNamespace(expires_at=target, tx_hash="0xreceipt", receipt={"gasUsed": "0x1", "effectiveGasPrice": "0x1"})

    worker = RenewalWorker(state_path=tmp_path / "renew.sqlite", games=games(), submitter=submit)
    first = worker.run_once(data, dry_run=False)
    assert all(row["status"] == "complete" for row in first["targets"])
    assert len(calls) == 3  # root, revision, and current comment evidence
    # Receipt-backed jobs remain complete when the same snapshot is replayed.
    worker.run_once(data, dry_run=False)
    assert len(calls) == 3
    with worker._db() as db:
        jobs = db.execute("SELECT target,credits,status FROM jobs ORDER BY entity").fetchall()
    assert len(jobs) == 3 and all(row[2] == "complete" for row in jobs)
    assert all(json.loads(row[1]) for row in jobs)
