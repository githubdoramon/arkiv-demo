from __future__ import annotations

import json
import math
from pathlib import Path

from arkiv_reviews.domain import validate_snapshot
from arkiv_reviews.reputation import VoteEvent, calculate_scores, events_from_entities, voter_weight

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((ROOT / "shared" / "reputation-fixtures.json").read_text())
CATALOG = json.loads((ROOT / "shared" / "games.json").read_text())


def test_shared_fixture_scores_are_exact_and_current_day_votes_count() -> None:
    snapshot = {
        "chain_id": FIXTURE["chain_id"],
        "block_number": 20,
        "block_timestamp": FIXTURE["evaluation_day"] * 86_400,
        "evaluation_day": FIXTURE["evaluation_day"],
        "entities": FIXTURE["entities"],
    }
    validated = validate_snapshot(snapshot, CATALOG)
    revision_authors = {r["key"]: r["payload"]["author"] for r in validated["revisions"]}
    scores = calculate_scores(
        events_from_entities(validated["votes"], revision_authors),
        evaluation_day=FIXTURE["evaluation_day"],
        known_wallets=set(revision_authors.values()),
    )
    for wallet, expected in FIXTURE["expected_scores"].items():
        assert math.isclose(scores[wallet], expected, rel_tol=0, abs_tol=1e-12)
    author = "0x0000000000000000000000000000000000000001"
    assert scores[author] == 0.002  # today's two votes count in the returned projection


def test_same_day_votes_use_day_start_weights_but_count_today() -> None:
    events = [
        VoteEvent("a", "0x02", "0x01", "helpful", 100, 1),
        VoteEvent("b", "0x01", "0x03", "helpful", 101, 2),
        # C has gained influence from B's prior-day vote, but C's vote today still uses C's
        # frozen day-start score of zero.
        VoteEvent("c", "0x03", "0x01", "helpful", 101, 3),
    ]
    scores = calculate_scores(events, evaluation_day=101)
    prior_a = 0.001 * 2 ** (-1 / 90)
    assert math.isclose(scores["0x01"], prior_a + 0.001, rel_tol=0, abs_tol=1e-12)
    assert scores["0x03"] > 0.001  # A's prior-day score raises A's event-day weight.
    assert voter_weight(0) == 0.001


def test_self_feedback_and_repeated_interactions_are_bounded() -> None:
    events = [
        VoteEvent("self", "a", "a", "helpful", 1, 1),
        VoteEvent("one", "v", "a", "helpful", 1, 2),
        VoteEvent("two", "v", "a", "helpful", 1, 3),
    ]
    score = calculate_scores(events, evaluation_day=1)["a"]
    assert score == 0.0015  # self ignored; second interaction contributes half of baseline.
