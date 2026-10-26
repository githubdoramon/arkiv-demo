"""Deterministic, expiry-aware review reputation projection.

Scores are derived from currently queryable canonical vote entities. The function intentionally
does not persist a score and does not claim permanent evidence or Sybil resistance.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

HALF_LIFE_DAYS = 90
REPEAT_WINDOW_DAYS = 30
MAX_REPEAT_COUNT = 5
MAX_SCORE = 1000.0


@dataclass(frozen=True)
class VoteEvent:
    key: str
    voter: str
    author: str
    value: str
    day: int
    block: int


def voter_weight(reputation: float) -> float:
    """Map a nonnegative reputation score to the demo's bounded vote influence."""
    score = max(0.0, min(MAX_SCORE, float(reputation)))
    return 0.001 + 0.999 * score / (score + 20.0)


def events_from_entities(
    votes: list[dict[str, Any]],
    revision_authors: dict[str, str],
) -> list[VoteEvent]:
    """Resolve each vote's author from its exact target revision, never from a newer edit."""
    events: list[VoteEvent] = []
    for vote in votes:
        payload = vote.get("payload")
        if not isinstance(payload, dict):
            continue
        target = payload.get("target_revision_key")
        author = revision_authors.get(target) if isinstance(target, str) else None
        if author is None:
            continue
        events.append(
            VoteEvent(
                key=str(vote.get("key", "")).lower(),
                voter=str(payload.get("voter", "")).lower(),
                author=author.lower(),
                value=str(payload.get("value", "")),
                day=int(vote.get("created_at_timestamp", 0)) // 86_400,
                block=int(vote.get("created_at_block", 0)),
            )
        )
    return events


def calculate_scores(
    events: list[VoteEvent], *, evaluation_day: int, known_wallets: set[str] | None = None
) -> dict[str, float]:
    """Replay currently queryable events and return scores through evaluation_day.

    All vote weights on a UTC day use scores computed from earlier days only. Events in one day are
    ordered by `(day, block, key)` for repeated-interaction diminishing returns, but they cannot
    recursively raise each other's weight that day. Current-day votes do contribute to the returned
    score with zero-day decay, so feedback appears immediately. Expired records must be omitted by
    the caller's same-block Arkiv snapshot; later snapshots can therefore produce a different replay.
    """
    ordered = sorted(events, key=lambda event: (event.day, event.block, event.key.lower()))
    by_day: dict[int, list[VoteEvent]] = defaultdict(list)
    for event in ordered:
        if event.day <= evaluation_day:
            by_day[event.day].append(event)

    users = {user.lower() for user in known_wallets or set()}
    users.update(event.voter.lower() for event in ordered)
    users.update(event.author.lower() for event in ordered)

    # Each contribution retains its original day so decay can be applied deterministically.
    contributions: list[tuple[str, int, float]] = []
    interactions: list[tuple[int, str, str]] = []

    for day in sorted(by_day):
        start_scores = _scores_at(contributions, day, users)
        for event in by_day[day]:
            voter, author = event.voter.lower(), event.author.lower()
            if not voter or not author or voter == author:
                continue
            if event.value not in {"helpful", "unhelpful"}:
                continue
            repeat_count = 1 + sum(
                1
                for prior_day, prior_voter, prior_author in interactions
                if prior_voter == voter
                and prior_author == author
                and 0 <= day - prior_day < REPEAT_WINDOW_DAYS
            )
            repeat_factor = 1.0 / repeat_count if repeat_count <= MAX_REPEAT_COUNT else 0.0
            sign = 1.0 if event.value == "helpful" else -1.0
            delta = sign * voter_weight(start_scores.get(voter, 0.0)) * repeat_factor
            contributions.append((author, day, delta))
            interactions.append((day, voter, author))

    return _scores_at(contributions, evaluation_day, users)


def _scores_at(
    contributions: list[tuple[str, int, float]], day: int, users: set[str]
) -> dict[str, float]:
    totals: dict[str, float] = {user: 0.0 for user in users}
    for author, event_day, delta in contributions:
        totals[author] = totals.get(author, 0.0) + delta * 2 ** (
            -(day - event_day) / HALF_LIFE_DAYS
        )
    return {user: max(0.0, min(MAX_SCORE, value)) for user, value in totals.items()}
