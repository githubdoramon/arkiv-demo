# Product code

This is the runnable SDK showcase. The product is an open game-review network with a Python backend and two separate browser clients.

| Folder | Responsibility |
| --- | --- |
| `poc/` | Small Arkiv Python SDK experiments |
| `backend/` | Python API, record validation, reputation, renewals and moderation |
| `frontends/review-app/` | Main wallet-connected review experience |
| `frontends/portfolio/` | Independent reviewer portfolio reading Arkiv directly |
| `frontends/shared/` | TypeScript chain access, schemas and deterministic calculations |
| `shared/` | Curated catalog, language-neutral contract and cross-client fixtures |
| `scripts/` | Local node, seeded example records and demo launcher |

From the repository root, start the assembled demo with:

```sh
python3 scripts/demo.py
```

Prerequisites: Docker running, Python 3.11+, `uv`, Node.js 22+ and npm. The sibling SDK checkouts must sit beside this repository: `../arkiv-python-sdk` and `../arkiv-sdk-js`.

The launcher installs dependencies, starts the pinned local Arkiv node, seeds example records through the Python SDK, starts the local Python renewal keeper, and serves:

- Reviews: <http://127.0.0.1:5173>
- Independent portfolio: <http://127.0.0.1:5174>
- Python API documentation: <http://127.0.0.1:8000/docs>

Use `--skip-install` after the first setup; `--no-seed` leaves existing chain records alone. Seeding is repeatable and reuses existing logical records. All example reviews and authors are fictional demo content, actually stored on the local chain.

Ctrl-C stops the launcher-owned servers while preserving the local chain for the next run. `bash scripts/devnode.sh stop` stops that chain; `remove` removes only its container. Chain data remains in ignored `.runtime/node-data/`. Those commands operate only on this demo's labeled container.

The wallet shortcuts and published development keys are restricted to loopback chain 1337. The public testnet build is documented in [deployment setup](deploy/README.md); it uses separate private test accounts and Tiramisu test GLM.
