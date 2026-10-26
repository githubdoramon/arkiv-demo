from __future__ import annotations

import copy
import json
from pathlib import Path

from arkiv_reviews.domain import validate_snapshot

ROOT = Path(__file__).resolve().parents[2]
CATALOG = json.loads((ROOT / "shared" / "games.json").read_text())
FIXTURE = json.loads((ROOT / "shared" / "reputation-fixtures.json").read_text())


def snapshot_from_fixture() -> dict:
    return {
        "chain_id": FIXTURE["chain_id"],
        "block_number": 20,
        "block_timestamp": FIXTURE["evaluation_day"] * 86_400,
        "evaluation_day": FIXTURE["evaluation_day"],
        "entities": copy.deepcopy(FIXTURE["entities"]),
    }


def test_fixture_canonicalizes_revision_chain_and_keeps_old_vote_target() -> None:
    result = validate_snapshot(snapshot_from_fixture(), CATALOG)
    assert len(result["roots"]) == 1
    assert [revision["payload"]["revision"] for revision in result["revisions"]] == [1, 2]
    assert result["latest_reviews"][0]["latest_revision"]["key"].endswith("3" * 64)
    assert result["votes"][0]["payload"]["target_revision_key"].endswith("2" * 64)
    assert result["invalid_entity_keys"] == []


def test_longest_valid_fork_wins_and_tie_break_is_stable() -> None:
    snapshot = snapshot_from_fixture()
    entities = snapshot["entities"]
    root = entities[0]
    rev1 = entities[1]
    rev2 = entities[2]
    branch2 = copy.deepcopy(rev2)
    branch2["key"] = "0x" + "6" * 64
    branch2["created_at_block"] = 4
    branch2["payload"]["logical_id"] = f"{root['key']}:revision:2"
    branch2["attributes"]["logical_id"] = f"{root['key']}:revision:2"
    branch3 = copy.deepcopy(branch2)
    branch3["key"] = "0x" + "7" * 64
    branch3["created_at_block"] = 5
    branch3["payload"].update(
        revision=3,
        previous_revision_key=branch2["key"],
        logical_id=f"{root['key']}:revision:3",
    )
    branch3["attributes"].update(revision=3, logical_id=f"{root['key']}:revision:3")
    snapshot["entities"].extend([branch2, branch3])

    result = validate_snapshot(snapshot, CATALOG)
    assert [r["key"] for r in result["revisions"]] == [rev1["key"], branch2["key"], branch3["key"]]


def test_mismatched_creator_is_excluded_and_reported() -> None:
    snapshot = snapshot_from_fixture()
    tampered = copy.deepcopy(snapshot["entities"][-1])
    tampered["key"] = "0x" + "8" * 64
    tampered["creator"] = "0x0000000000000000000000000000000000000009"
    snapshot["entities"].append(tampered)

    result = validate_snapshot(snapshot, CATALOG)
    assert len(result["votes"]) == 2
    assert tampered["key"] in result["invalid_entity_keys"]


def test_duplicate_root_and_vote_choose_earliest_block_then_key() -> None:
    snapshot = snapshot_from_fixture()
    root_duplicate = copy.deepcopy(snapshot["entities"][0])
    root_duplicate["key"] = "0x" + "9" * 64
    root_duplicate["created_at_block"] = 50
    vote_duplicate = copy.deepcopy(snapshot["entities"][3])
    vote_duplicate["key"] = "0x" + "a" * 64
    vote_duplicate["created_at_block"] = 50
    snapshot["entities"].extend([root_duplicate, vote_duplicate])

    result = validate_snapshot(snapshot, CATALOG)
    assert [root["key"] for root in result["roots"]] == [snapshot["entities"][0]["key"]]
    assert len(result["votes"]) == 2
    assert result["votes"][0]["key"] == snapshot["entities"][3]["key"]
