# Sidequest and Afterword frontends

Two local React + Vite clients share a TypeScript snapshot and canonicalization/reputation domain:

- Sidequest review app: `http://127.0.0.1:5173` (reads through the Python API; writes directly from the browser wallet through the sibling Arkiv JS SDK).
- Afterword independent portfolio: `http://127.0.0.1:5174` (reads Arkiv directly at one pinned block; does not call the Python API).

From this directory:

```sh
cp .env.example .env.local
npm ci
npm run dev:review
npm run dev:portfolio
npm run build
npm run typecheck
npm test
```

`npm test` runs both client type checks and deterministic fixtures against the Python-derived expected canonical record keys and reputation scores in `shared/domain-fixtures.json`, plus the shared same-day score fixture in `shared/reputation-fixtures.json`.

The repo integrator may launch either Vite app independently. The shared build is a workspace source package. `VITE_ARKIV_RPC_URL` defaults to the local node at `127.0.0.1:18547`; `VITE_API_URL` defaults to `127.0.0.1:8000`. Both can be changed in `.env.local`. Local development wallets are fixed published Hardhat keys, enabled only for loopback RPC after the app verifies chain id 1337. An injected EIP-1193 wallet must also report chain id 1337 before writes. No private key is sent to the API.

Game covers reference publisher-hosted artwork URLs listed in `shared/ARTWORK.md`; this repository does not redistribute local copies of publisher-owned art. Both apps share neutral light/dark theme tokens. Snapshot/debug details stay out of the player interface. Reputation is recomputed from active canonical records using the shared TypeScript implementation. Review records and feedback are append-only, and votes stay attached to the exact revision they name.

Browser wallet connection switches to the local network and requests adding it when missing. The wallet may ask the user to approve those requests. The local native currency is labeled test GLM. Operator visibility controls are available on the review app with `?admin=1`.

## Tiramisu production builds

`npm run build:tiramisu` uses `.env.tiramisu` from this workspace directory, selects chain 7738577, uses same-origin `/api` for the main app and compiles links to `https://sidequest.appcalipse.com/` and `https://afterword.appcalipse.com/`. Local development wallet choices are omitted, and entity/transaction links use Arkiv's public explorers. Both Vite apps read their env files from this workspace directory. `npm run build` retains the default local configuration. Docker packaging is documented in `../deploy/README.md`.

## Visual identities

Sidequest uses the approved dark console-style cover collection; Afterword uses the approved light editorial reviewer layout. Each app has its own `DESIGN.md` and token sidecar. Player-facing account controls say **Sign in** and **My profile**. On local builds, Sign in offers Reviewer one / Reviewer two demo accounts. Wallet approval is explained only when it is needed. Existing exported Docker bundles need rebuilding to include this redesign. See `../deploy/README.md` for packaging and upgrade instructions. Design and motion rules live in each app’s `DESIGN.md`. Local browser verification artifacts are generated under `output/` and are not committed.
