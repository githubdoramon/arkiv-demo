# Sidequest and Afterword on Tiramisu: two containers

The release is built for **linux/amd64**, with these public URLs already compiled into both frontends:

- `https://sidequest.appcalipse.com/` → review container, port 8080
- `https://afterword.appcalipse.com/` → portfolio container, port 8081

The review container includes nginx, our Python SDK backend and an optional Python renewal keeper. The independent portfolio container serves its own frontend and reads Tiramisu directly. No local Arkiv node, source checkout, npm or Python installation is needed on the server. Tiramisu chain ID is 7738577. Wallets switch/add that network automatically. The browser API URL is same-origin `/api`; no localhost links or development wallet choices are shown in the testnet UI. Data links use Arkiv's public explorers.

## Build and package on the development machine

Keep both sibling SDK checkouts next to this repository, then run from the repository root (the folder containing `scripts/`, `frontends/` and `backend/`):

```sh
python3 scripts/package_testnet.py
```

This builds `sidequest-review:tiramisu` and `sidequest-portfolio:tiramisu` with Docker Compose/BuildKit and creates `.runtime/releases/sidequest-tiramisu-amd64.zip` and a SHA-256 checksum. Only the required SDK source files enter image layers. Runtime wallets, browser output, local chain data and `.env.local` files are excluded. The packager resolves sibling SDKs automatically, including this repository nested under the challenge workspace. For other layouts set `ARKIV_JS_CONTEXT` and `ARKIV_PYTHON_CONTEXT` to absolute checkout paths. Re-run with `--skip-build` to re-export already-built images. Add `--format tar.gz` only if you need the older archive format.

## Run the exported package on the server

```sh
unzip sidequest-tiramisu-amd64.zip
cd sidequest-tiramisu-amd64
gunzip -c images.tar.gz | docker load
test -f .env || cp .env.example .env
docker compose up -d --no-build
docker compose ps
```

## Upgrade an existing installation

Unzip the new release over the existing release directory. The ZIP contains `.env.example`, not `.env`, and an empty `secrets/` directory, never your runtime keys. Run the following from the parent of the existing release directory (the one holding your `compose.yaml`, `.env` and `secrets/`):

```sh
# Run from the parent of the existing sidequest-tiramisu-amd64 directory:
unzip -o sidequest-tiramisu-amd64.zip
cd sidequest-tiramisu-amd64
gunzip -c images.tar.gz | docker load
docker compose up -d --no-build --force-recreate
docker compose ps
```

Keep your existing `.env`, `secrets/keeper.key` and `sidequest-data` volume. Do not copy the packaged initial ledger over existing server state, and do not use `docker compose down -v` during an upgrade. The Compose project and service names stay the same so existing state is reused.

Change the portfolio DNS/HTTPS reverse-proxy host from the old portfolio domain to **afterword.appcalipse.com**. It still uses port **8081**; Sidequest remains on port **8080**. Both apps are compiled with the new cross-domain links. Keep the old host as a redirect to the new host if desired.

Configure your existing HTTPS reverse proxy:

| HTTPS host | Upstream |
| --- | --- |
| sidequest.appcalipse.com | http://127.0.0.1:8080 |
| afterword.appcalipse.com | http://127.0.0.1:8081 |

Both DNS records must point to the server. HTTPS is needed for normal browser-wallet use on these domains. Default bindings are loopback, suitable for a proxy on the host. For a containerized proxy, connect it to the Compose network and use `app:8080` and `portfolio:8080`, or deliberately adjust `SIDEQUEST_BIND` in `.env` for your network. Persistent moderation and renewal state is stored in the `sidequest-data` Docker volume. Review/profile data is on Tiramisu.

```sh
curl http://127.0.0.1:8080/healthz
curl http://127.0.0.1:8080/api/health
curl http://127.0.0.1:8081/healthz
docker compose logs --tail=80
```

`/healthz` checks the running process; `/api/health` also verifies the public RPC and chain. A static portfolio health check does not imply the public RPC is reachable.

## Funding and seeding (development machine)

Private accounts are stored outside the image context at `.runtime/tiramisu/wallets.json`, with file mode 0600. Commands print only addresses and balances.

```sh
uv run --project backend python scripts/testnet_wallets.py init
uv run --project backend python scripts/testnet_wallets.py status
uv run --project backend python scripts/seed.py --network tiramisu
```

Fund the printed **funding** address with test GLM on Tiramisu first. The seed command tops up each of the three authors to 0.1 GLM and the keeper to 0.2 GLM, requiring approximately 0.5 GLM plus transfer fees on its first run. If the funding wallet is short, it reports the required balance and stops. It then writes three demo profiles, eight reviews, eight helpful votes and three comments with our Python SDK. Re-runs reuse existing creator/logical identities and top up balances only as needed. Nothing is seeded automatically at server startup.

Public-network writes are real testnet transactions. Seed accounts and their data are separate from the local demo. Never put a wallet key in a `VITE_` variable, Docker build argument, image or public configuration.

## Enable automatic renewals

Export only the keeper key; the funding and author keys can remain on the development machine:

```sh
uv run --project backend python scripts/testnet_wallets.py export-keeper --output .runtime/tiramisu/keeper.key
```

On a **fresh** server installation, if the release includes `state/renewal.sqlite3`, copy that initial ledger before enabling the keeper:

```sh
docker compose cp state/renewal.sqlite3 app:/data/renewal.sqlite3
```

This preserves credits already processed during the testnet smoke test. Skip this on upgrades with an existing live data volume; never overwrite a running keeper's ledger.

Transfer the exported key privately to `secrets/keeper.key` inside the unpacked server release directory, preserve its private permissions, then run:

```sh
docker compose restart app
```

`KEEPER_ENABLED=auto` starts the keeper when its runtime key file exists. Use `1` to require it or `0` to disable it. The key is passed only to the keeper process. The backend remains read-only with respect to users' Arkiv records. The default renewal budget remains 0.1 GLM per day. Keeper state survives container replacement through the data volume.

The release includes an empty `secrets/` directory, never its files, even when the package output directory is reused. Keep a private backup of `wallets.json` and the keeper key; do not publish them with the demo.
