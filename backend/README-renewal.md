# Renewal and moderation demo controls

The worker and moderation queue are local showcase helpers. Arkiv remains the source for review content and reputation. The SQLite files are disposable local idempotency/moderation state, not authoritative review data.

## Renewal worker

`arkiv_reviews.renewal.RenewalWorker(rpc_url, keeper_key, state_path, daily_budget_glm=0.1)` consumes the normalized current-only snapshot described in `shared/CONTRACT.md`:

```python
worker = RenewalWorker(
    rpc_url="http://127.0.0.1:18547",
    keeper_key=os.environ.get("ARKIV_KEEPER_PRIVATE_KEY"),
    state_path="./runtime/renewal.sqlite3",
)
result = worker.run_once(snapshot, dry_run=True)  # default; no signing
```

Set `ARKIV_RENEWAL_DAILY_BUDGET_GLM` to change the default 0.1 GLM daily ceiling. Live submission requires calling `run_once(..., dry_run=False)` and a funded keeper configured with `ARKIV_KEEPER_PRIVATE_KEY`. It uses the sibling Python SDK's `Arkiv.extend_entity` with an absolute `ExpirationTime.at_block(target)` deadline. The SDK waits for the transaction receipt; the worker checks the confirmed expiry and records its hash/receipt. The local job ledger fixes a baseline and target, tracks consumed actor/root evidence IDs, reconciles already-applied targets, and backs off failed submissions.

One canonical non-self Helpful vote or valid comment from an actor on a canonical review root earns up to seven days weighted by the core reputation projection at the start of that UTC event day. More activity by that actor/root inside the trailing 30-day window does not add credit. The root's aggregate credit is capped at 30 days in any trailing 30 days and edits do not reset the ledger. Each credit extends the root, its canonical revision chain, and the currently queryable canonical vote/comment evidence attached to those revisions by the same amount, keeping the demo review/evidence set together. Unhelpful votes earn none. Dry-run persists a stable plan but does not consume credit eligibility; running live against the same snapshot applies that plan. `run_once` reports `dry-run`, `complete`, `retryable`, `backoff`, `budget-exhausted`, `expired`, and `no-op` statuses.

This is a small local keeper, not a scheduler or production budget service. Keep the state file between runs. A first transaction can only be checked against actual charged gas after its receipt is mined; unknown receipt cost consumes the full configured ceiling so the worker stops after that transaction for the day. Use only a small test-token balance.

## Moderation API

The core API mounts `build_router()` from `arkiv_reviews.moderation`; it serves:

- `POST /api/reports` with `{reporter, entity_key, reason, details?, signature}`. `reason` is `spam`, `abuse`, `off_topic`, or `other`. The wallet signs this exact EIP-191 text (details are trimmed):

  ```text
  Arkiv review report
  reporter:<lowercase wallet>
  entity_key:<lowercase bytes32 key>
  reason:<reason>
  details:<details or empty>
  ```

  The backend recovers and matches the reporter, then returns `{report_id}`. Per-wallet and per-network hourly limits are applied.
- `GET /api/moderation` returns `{hidden_keys:[...]}` for public display filtering.
- `PUT /api/moderation/{entity_key}` with `{hidden:boolean, reason}` and `Authorization: Bearer <MODERATOR_TOKEN>` hides/unhides a key. Keep `MODERATOR_TOKEN` server-side; an unset token disables operator writes.

Set `ARKIV_MODERATION_DB` to choose the local SQLite report queue; default is `./runtime/moderation.sqlite3`. Reports and hide state do not alter Arkiv records, canonicalization, or reputation. The local queue has no multi-instance replication or anti-abuse claim.

## Focused checks

From the repository root, run `uv run --project backend --extra dev pytest backend/tests/test_renewal_controls.py backend/tests/test_moderation_controls.py`.
