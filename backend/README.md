# Python review backend

Read-only FastAPI service for the review showcase. It uses the sibling Python SDK as an editable path dependency; browser wallets write Arkiv entities directly and never send private keys to this service.

## Setup and run

From this directory:

```sh
uv sync --extra dev
ARKIV_RPC_URL=http://127.0.0.1:18547 uv run uvicorn arkiv_reviews.api:app --host 127.0.0.1 --port 8000
```

The default RPC is the loopback devnode at port 18547. Production/testnet callers must explicitly set their RPC URL. The API has `GET /api/health`, `/api/catalog`, `/api/snapshot`, and `/api/reputation`. Development CORS allows both configured frontend origins on ports 5173 and 5174. Moderation routes are mounted from `arkiv_reviews.moderation.build_router()` when that module is present.

Run the focused backend checks with:

```sh
uv run pytest
```

`/api/snapshot` paginates the `app=arkiv-review-demo` query at a single block and resolves creation timestamps from RPC block headers. `/api/reputation` validates the same snapshot and returns a deterministic projection from the canonical, currently queryable vote set. It includes today's votes immediately while using start-of-day voter influence for all votes made on the same UTC day.
