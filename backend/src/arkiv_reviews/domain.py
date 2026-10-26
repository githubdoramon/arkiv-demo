"""Validation and deterministic duplicate/fork selection for normalized Arkiv snapshots."""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

APP_ID = "arkiv-review-demo"


def normalize_wallet(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) != 42 or not value.startswith("0x"):
        return None
    try:
        int(value, 0)
    except ValueError:
        return None
    return value.lower()


def normalize_key(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) != 66 or not value.startswith("0x"):
        return None
    try:
        int(value, 0)
    except ValueError:
        return None
    return value.lower()


def _created_order(entity: dict[str, Any]) -> tuple[int, str]:
    return (int(entity.get("created_at_block") or 0), str(entity.get("key", "")).lower())


def _payload(entity: dict[str, Any], schema: str) -> dict[str, Any] | None:
    value = entity.get("payload")
    if isinstance(value, dict) and value.get("schema") == schema:
        return value
    return None


def _attributes(entity: dict[str, Any]) -> dict[str, Any]:
    attrs = entity.get("attributes")
    return attrs if isinstance(attrs, dict) else {}


def _valid_base(entity: dict[str, Any], kind: str) -> bool:
    key = normalize_key(entity.get("key"))
    creator = normalize_wallet(entity.get("creator"))
    return bool(
        key
        and creator
        and _attributes(entity).get("app") == APP_ID
        and _attributes(entity).get("kind") == kind
    )


def _has_flags(entity: dict[str, Any], *, readonly: bool) -> bool:
    flags = entity.get("flags")
    return bool(
        isinstance(flags, dict)
        and flags.get("readonly") is readonly
        and flags.get("permissionless_extension") is True
    )


def _canonical_entities(entities: list[dict[str, Any]], id_key: Any) -> list[dict[str, Any]]:
    groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for entity in entities:
        groups[id_key(entity)].append(entity)
    return [
        min(group, key=_created_order)
        for _, group in sorted(groups.items(), key=lambda item: str(item[0]))
    ]


def _revision_chains(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find valid revision-1-to-tip chains; longest wins, with stable fork tie-breaking."""
    by_parent_and_number: dict[tuple[str | None, int], list[dict[str, Any]]] = defaultdict(list)
    for revision in candidates:
        payload = revision["payload"]
        by_parent_and_number[(payload.get("previous_revision_key"), payload["revision"])].append(
            revision
        )
    for values in by_parent_and_number.values():
        values.sort(key=_created_order)

    def paths_from(revision: dict[str, Any]) -> list[list[dict[str, Any]]]:
        p = revision["payload"]
        children = by_parent_and_number.get((revision["key"], p["revision"] + 1), [])
        if not children:
            return [[revision]]
        result: list[list[dict[str, Any]]] = []
        for child in children:
            result.extend([[revision, *path] for path in paths_from(child)])
        return result

    roots = by_parent_and_number.get((None, 1), [])
    paths = [path for root in roots for path in paths_from(root)]
    if not paths:
        return []
    # Longest contiguous chain; for equal length choose the lexicographically earliest sequence.
    return min(paths, key=lambda path: (-len(path), tuple(_created_order(x) for x in path)))


def validate_snapshot(snapshot: dict[str, Any], games: list[dict[str, Any]]) -> dict[str, Any]:
    """Return canonical, schema-valid records and latest reviews from one raw snapshot.

    Invalid records are listed by entity key for operator visibility but omitted from all app
    projections. Entity keys, authors, wallets, and references are compared case-insensitively.
    """
    entities = snapshot.get("entities", [])
    if not isinstance(entities, list):
        raise TypeError("snapshot.entities must be a list")
    game_by_id = {game.get("id"): game for game in games if isinstance(game, dict)}
    invalid: set[str] = set()

    def reject(entity: dict[str, Any]) -> None:
        invalid.add(str(entity.get("key", "")).lower())

    profile_candidates: list[dict[str, Any]] = []
    root_candidates: list[dict[str, Any]] = []
    revision_candidates: list[dict[str, Any]] = []
    vote_candidates: list[dict[str, Any]] = []
    comment_candidates: list[dict[str, Any]] = []

    for entity in entities:
        if not isinstance(entity, dict) or _attributes(entity).get("app") != APP_ID:
            continue
        kind = _attributes(entity).get("kind")
        schema_by_kind = {
            "profile": "profile/v1",
            "review-root": "review-root/v1",
            "review-revision": "review-revision/v1",
            "review-vote": "review-vote/v1",
            "review-comment": "review-comment/v1",
        }
        expected_schema = schema_by_kind.get(kind)
        if expected_schema is None:
            continue
        if not _valid_base(entity, kind):
            reject(entity)
            continue
        payload = _payload(entity, expected_schema)
        attrs = _attributes(entity)
        creator = normalize_wallet(entity.get("creator"))
        key = normalize_key(entity.get("key"))
        if payload is None or key is None:
            reject(entity)
            continue
        entity = {
            **entity,
            "key": key,
            "creator": creator,
            "owner": normalize_wallet(entity.get("owner")),
            "payload": payload,
        }

        if kind == "profile":
            wallet = normalize_wallet(payload.get("wallet"))
            logical = f"profile:{snapshot['chain_id']}:{wallet}" if wallet else None
            if (
                wallet != creator
                or payload.get("logical_id") != logical
                or normalize_wallet(attrs.get("wallet")) != wallet
                or attrs.get("logical_id") != logical
                or not isinstance(payload.get("display_name"), str)
                or not payload["display_name"].strip()
                or not _has_flags(entity, readonly=False)
            ):
                reject(entity)
            else:
                entity["payload"] = {**payload, "wallet": wallet}
                profile_candidates.append(entity)
        elif kind == "review-root":
            author = normalize_wallet(payload.get("author"))
            game_id, platform = payload.get("game_id"), payload.get("platform")
            logical = (
                f"review:{snapshot['chain_id']}:{author}:{game_id}:{platform}" if author else None
            )
            game = game_by_id.get(game_id)
            if (
                author != creator
                or not game
                or platform not in game.get("platforms", [])
                or payload.get("logical_id") != logical
                or normalize_wallet(attrs.get("author")) != author
                or attrs.get("game_id") != game_id
                or attrs.get("platform") != platform
                or attrs.get("logical_id") != logical
                or not _has_flags(entity, readonly=True)
            ):
                reject(entity)
            else:
                entity["payload"] = {**payload, "author": author}
                root_candidates.append(entity)
        elif kind == "review-revision":
            root_key = normalize_key(payload.get("root_key"))
            author = normalize_wallet(payload.get("author"))
            revision_number = payload.get("revision")
            previous_key = payload.get("previous_revision_key")
            rating = payload.get("rating_half_stars")
            text = payload.get("text")
            if (
                root_key is None
                or type(revision_number) is not int
                or revision_number < 1
                or (revision_number == 1 and previous_key is not None)
                or (revision_number > 1 and normalize_key(previous_key) is None)
                or type(rating) is not int
                or not 2 <= rating <= 10
                or not isinstance(text, str)
                or not text.strip()
                or author != creator
                or payload.get("logical_id") != f"{root_key}:revision:{revision_number}"
                or normalize_key(attrs.get("root_key")) != root_key
                or attrs.get("revision") != revision_number
                or attrs.get("logical_id") != payload.get("logical_id")
                or not _has_flags(entity, readonly=True)
            ):
                reject(entity)
            else:
                entity["payload"] = {
                    **payload,
                    "root_key": root_key,
                    "author": author,
                    "previous_revision_key": normalize_key(previous_key) if previous_key else None,
                }
                revision_candidates.append(entity)
        elif kind == "review-vote":
            target = normalize_key(payload.get("target_revision_key"))
            voter = normalize_wallet(payload.get("voter"))
            logical = f"vote:{target}:{voter}" if target and voter else None
            if (
                voter != creator
                or payload.get("value") not in {"helpful", "unhelpful"}
                or payload.get("logical_id") != logical
                or normalize_key(attrs.get("target_revision_key")) != target
                or normalize_wallet(attrs.get("voter")) != voter
                or attrs.get("logical_id") != logical
                or not _has_flags(entity, readonly=True)
            ):
                reject(entity)
            else:
                entity["payload"] = {**payload, "target_revision_key": target, "voter": voter}
                vote_candidates.append(entity)
        else:  # review-comment
            target = normalize_key(payload.get("target_revision_key"))
            author = normalize_wallet(payload.get("author"))
            logical = payload.get("logical_id")
            comment_id = (
                logical[len("comment:") :]
                if isinstance(logical, str) and logical.startswith("comment:")
                else ""
            )
            try:
                valid_uuid = str(UUID(comment_id)) == comment_id.lower()
            except (ValueError, AttributeError):
                valid_uuid = False
            if (
                author != creator
                or target is None
                or not valid_uuid
                or not isinstance(payload.get("text"), str)
                or not payload["text"].strip()
                or normalize_key(attrs.get("target_revision_key")) != target
                or normalize_wallet(attrs.get("author")) != author
                or attrs.get("logical_id") != logical
                or not _has_flags(entity, readonly=True)
            ):
                reject(entity)
            else:
                entity["payload"] = {**payload, "target_revision_key": target, "author": author}
                comment_candidates.append(entity)

    profiles = _canonical_entities(profile_candidates, lambda entity: entity["payload"]["wallet"])
    roots = _canonical_entities(
        root_candidates,
        lambda entity: (
            entity["payload"]["author"],
            entity["payload"]["game_id"],
            entity["payload"]["platform"],
        ),
    )
    root_by_key = {root["key"]: root for root in roots}

    orphan_revisions = [
        revision
        for revision in revision_candidates
        if revision["payload"]["root_key"] not in root_by_key
    ]
    for entity in orphan_revisions:
        reject(entity)
    revision_candidates = [r for r in revision_candidates if r not in orphan_revisions]
    for revision in revision_candidates:
        root = root_by_key[revision["payload"]["root_key"]]
        if revision["payload"]["author"] != root["payload"]["author"]:
            reject(revision)
    revision_candidates = [r for r in revision_candidates if r["key"] not in invalid]

    latest_reviews: list[dict[str, Any]] = []
    canonical_revisions: list[dict[str, Any]] = []
    for root in roots:
        candidates = [r for r in revision_candidates if r["payload"]["root_key"] == root["key"]]
        chain = _revision_chains(candidates)
        canonical_revisions.extend(chain)
        if chain:
            latest_reviews.append({"root": root, "latest_revision": chain[-1], "revisions": chain})
    canonical_revision_by_key = {r["key"]: r for r in canonical_revisions}

    orphan_votes = [
        vote
        for vote in vote_candidates
        if vote["payload"]["target_revision_key"] not in canonical_revision_by_key
    ]
    for entity in orphan_votes:
        reject(entity)
    vote_candidates = [v for v in vote_candidates if v not in orphan_votes]
    votes = _canonical_entities(
        vote_candidates,
        lambda entity: (entity["payload"]["target_revision_key"], entity["payload"]["voter"]),
    )
    orphan_comments = [
        comment
        for comment in comment_candidates
        if comment["payload"]["target_revision_key"] not in canonical_revision_by_key
    ]
    for entity in orphan_comments:
        reject(entity)
    comment_candidates = [c for c in comment_candidates if c not in orphan_comments]
    comments = _canonical_entities(
        comment_candidates, lambda entity: entity["payload"]["logical_id"]
    )

    return {
        "chain_id": int(snapshot["chain_id"]),
        "block_number": int(snapshot["block_number"]),
        "block_timestamp": int(snapshot["block_timestamp"]),
        "evaluation_day": int(snapshot["evaluation_day"]),
        "profiles": profiles,
        "roots": roots,
        "revisions": canonical_revisions,
        "votes": votes,
        "comments": comments,
        "latest_reviews": latest_reviews,
        "invalid_entity_keys": sorted(key for key in invalid if key),
    }
