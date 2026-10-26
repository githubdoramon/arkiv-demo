"""Executable sanity fixtures for deterministic reputation: python proof/reputation_fixtures.py"""

from math import isclose

from reputation import Vote, reputation_at_day_start, voter_weight


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(f"FAIL {name}")
    print(f"PASS {name}")


def main() -> None:
    fresh = {"rev-a": "alice", "rev-b": "bob"}
    empty = reputation_at_day_start([], fresh, 1)
    check("fresh wallets start with equal influence", empty["alice"] == empty["bob"] == 0.0 and voter_weight(0) == 0.001)

    feedback = [Vote("v1", "alice", "rev-b", "helpful", 0, 1, 180)]
    one_day = reputation_at_day_start(feedback, fresh, 1)
    day_90 = reputation_at_day_start(feedback, fresh, 90)
    check("helpful vote earns reputation next day", one_day["bob"] > 0 and one_day["alice"] == 0)
    check("earned reputation decays with 90-day half-life", isclose(day_90["bob"], one_day["bob"] * 2 ** (-(89 / 90)), rel_tol=1e-12))

    # An edit creates another target key; it does not copy the old vote onto revision 2.
    revisions = {"rev-a": "alice", "rev-a2": "alice", "rev-b": "bob"}
    old_revision_vote = [Vote("v-old", "bob", "rev-a", "helpful", 0, 1, 180)]
    check("vote on old revision contributes once and remains keyed to that revision", reputation_at_day_start(old_revision_vote, revisions, 1)["alice"] > 0)
    check("self feedback is excluded", reputation_at_day_start([Vote("self", "alice", "rev-a", "helpful", 0, 1, 180)], revisions, 1)["alice"] == 0)
    check("expired evidence is removed from current replay", reputation_at_day_start([Vote("gone", "bob", "rev-a", "helpful", 0, 1, 1)], revisions, 2)["alice"] == 0)


if __name__ == "__main__":
    main()
