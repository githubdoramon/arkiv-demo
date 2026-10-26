# Sidequest data contract

Sidequest is a technical showcase for cross-client game reviews stored on Arkiv. The Python API provides a validated snapshot and local showcase helpers. Browser wallets write review entities through the JavaScript SDK; the independent portfolio reads Arkiv directly.

## Repository layout

- `poc/`: small Python SDK experiments.
- `backend/`: Python API, validation, reputation, renewal, and moderation.
- `frontends/review-app/`: wallet-connected review client.
- `frontends/portfolio/`: independent Arkiv-reading client.
- `frontends/shared/`: shared TypeScript schema and calculations.
- `shared/`: game catalog and cross-language fixtures.
- `scripts/`: local demo, seeding, and deployment helpers.

## Local runtime

The demo defaults to a local Arkiv node at `http://127.0.0.1:18547` (chain 1337), a Python API at `http://127.0.0.1:8000`, a review app at `http://127.0.0.1:5173`, and a portfolio app at `http://127.0.0.1:5174`. Published development wallets are limited to loopback RPC and chain 1337. Testnet configuration is documented in `deploy/README.md`.

## HTTP API

- `GET /api/health`: API and configured chain status.
- `GET /api/catalog`: curated game catalog.
- `GET /api/snapshot`: validated entities read at one chain block.
- `GET /api/reputation`: reputation scores derived from validated snapshot data.

Reputation includes feedback created on the evaluation UTC day. A vote's weight uses the voter's score at the start of its UTC day; votes on the same day share those starting scores.

Writes belong to the connected browser wallet; user private keys are never sent to the Python API. A local development wallet mode is labeled and guarded by loopback and chain checks. Normal wallet support uses an injected EIP-1193 provider.

## Snapshot shape

```json
{
  "chain_id": 1337,
  "block_number": 10,
  "block_timestamp": 1793016000,
  "evaluation_day": 20752,
  "entities": [{
    "key": "0x...",
    "creator": "0x...",
    "owner": "0x...",
    "created_at_block": 4,
    "created_at_timestamp": 1793015900,
    "expires_at_block": 7776004,
    "flags": {"readonly": true, "permissionless_extension": true},
    "attributes": {"app": "arkiv-review-demo", "kind": "review-revision"},
    "payload": {"schema": "review-revision/v1"}
  }]
}
```

Addresses and keys normalize to lowercase before comparison. Timestamps come from chain blocks rather than browser clocks. Attribute values are unwrapped from SDK tagged values. The portfolio constructs its snapshot directly from Arkiv instead of calling the Python API.

## Catalog and artwork

`games.json` contains curated games with stable lowercase IDs, title, year, genres, supported platform IDs, summary, and publisher-hosted cover URLs. Covers and optional hero images remain the property of their respective publishers; this repository references the remote URLs and does not redistribute local artwork copies. Remote image availability depends on the source host.

Ratings are half-star integers from 2 to 10. The latest canonical revision supplies a review's current rating. Schema validation and canonical record selection are implemented in `backend/src/arkiv_reviews/domain.py` and `frontends/shared/src/domain.ts`.

## Renewals and moderation

The renewal worker uses a SQLite ledger for local idempotency state; Arkiv remains the source for review content. It defaults to dry-run, with explicit configuration required for live submission. The moderation queue and operator controls are local showcase helpers and do not alter Arkiv records or reputation.
