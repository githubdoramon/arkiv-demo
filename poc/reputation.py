"""Small deterministic reputation reference for the showcase fixtures."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

HALF_LIFE_DAYS = 90
REPEAT_WINDOW_DAYS = 30
MAX_REPEAT_COUNT = 5


@dataclass(frozen=True)
class Vote:
    entity_key: str
    voter: str
    target_revision_key: str
    value: str
    created_day: int
    created_block: int
    expires_day: int


def reputation_at_day_start(
    votes: list[Vote], revision_authors: dict[str, str], evaluation_day: int
) -> dict[str, float]:
    """Replay currently visible votes; score inputs are frozen at each UTC day start.

    Entities are evidence only while expires_day > evaluation_day. Replaying the same current
    entity set in chronological order makes the result deterministic; expired evidence is removed
    from the replay and no permanent score is implied. The target revision key is always retained
    and looked up directly; a review edit never copies or retargets a vote.
    """
    visible = [v for v in votes if v.expires_day > evaluation_day]
    visible.sort(key=lambda v: (v.created_day, v.created_block, v.entity_key))
    by_day: dict[int, list[Vote]] = defaultdict(list)
    for vote in visible:
        if vote.created_day < evaluation_day:
            by_day[vote.created_day].append(vote)

    contributions: list[tuple[str, int, float]] = []
    interactions: list[tuple[int, str, str]] = []
    for day in sorted(by_day):
        # Freeze reputation from all earlier days. Same-day feedback cannot recursively boost
        # another vote on that same day.
        at_start: dict[str, float] = {}
        for user in set(revision_authors.values()) | {v.voter for v in visible}:
            raw = sum(
                delta * 2 ** (-(day - event_day) / HALF_LIFE_DAYS)
                for recipient, event_day, delta in contributions
                if recipient == user
            )
            at_start[user] = min(1000.0, max(0.0, raw))

        for vote in by_day[day]:
            author = revision_authors.get(vote.target_revision_key)
            if author is None or vote.voter.lower() == author.lower():
                continue
            prior = sum(
                1 for event_day, voter, recipient in interactions
                if voter.lower() == vote.voter.lower()
                and recipient.lower() == author.lower()
                and 0 <= day - event_day < REPEAT_WINDOW_DAYS
            )
            n = prior + 1
            repeat_factor = 1 / n if n <= MAX_REPEAT_COUNT else 0.0
            voter_score = at_start.get(vote.voter, 0.0)
            voter_weight = 0.001 + 0.999 * voter_score / (voter_score + 20)
            sign = 1.0 if vote.value == "helpful" else -1.0 if vote.value == "unhelpful" else 0.0
            if sign:
                contributions.append((author, day, sign * voter_weight * repeat_factor))
                interactions.append((day, vote.voter, author))

    result: dict[str, float] = {}
    for user in set(revision_authors.values()) | {v.voter for v in visible}:
        raw = sum(
            delta * 2 ** (-(evaluation_day - event_day) / HALF_LIFE_DAYS)
            for recipient, event_day, delta in contributions
            if recipient == user
        )
        result[user] = min(1000.0, max(0.0, raw))
    return result


def voter_weight(reputation: float) -> float:
    return 0.001 + 0.999 * reputation / (reputation + 20)
