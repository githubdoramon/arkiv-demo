# Arkiv review prototype

A small learning demo for the local Arkiv Python SDK. It is a technical proof of entity identity, immutable revisions, permissions, third-party renewal, and the data contract for a wallet-connected game-review MVP. It is not a business validation or a Sybil-resistance claim.

## Run the two-wallet proof locally

Run these commands from `poc/`. Python 3.10+, `uv`, and Docker are required. Start the same pinned disposable node image used by the sibling SDK integration setup, on a private loopback port:

```sh
docker run --detach --name arkiv-review-proof \
  --publish 127.0.0.1:18547:8545 \
  --publish 127.0.0.1:18548:8546 \
  ghcr.io/arkiv-network/arkiv-reth-dev@sha256:8204268426c2827f136a4fd0f422d61f11f503388df0f70a273c1227b6f6fb4d
```

Wait until `eth_chainId` returns `0x539` (1337) and the block number is above zero. This check is required before using the published local-only development keys below. The proof itself also checks chain id 1337 before constructing signing clients and refuses every other chain. Then install the project and sibling Python SDK dependencies:

```sh
uv sync
```

Set the two known, published Hardhat development keys (local node only), then run:

```sh
export ARKIV_RPC_URL=http://127.0.0.1:18547
export AUTHOR_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
export KEEPER_PRIVATE_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
uv run python two_wallet.py
uv run python reputation_fixtures.py
```

The author creates the review root and first revision; the keeper demonstrates rejected mutation, paid renewal, vote creation, and the root ownership transfer. The script also checks owner-authorized profile edits, read-only behavior for both owner and keeper, and a 1-wei native-token transfer from author to keeper. The native transfer proves local wallet funding works; the keeper still signs and pays its own renewal transaction. This does not prove a sponsored fee payer. No real funds are used.

Save any desired logs, then remove only this disposable container with `docker rm --force arkiv-review-proof`.

An entity key is printed only after a successful SDK transaction and readback. Expiry is block based and approximate in wall time. Keep the output if you want to inspect the demo records before they expire.

## What this proves and what it does not

The runnable proof is [`two_wallet.py`](two_wallet.py), with deterministic reference logic and sanity fixtures in [`reputation.py`](reputation.py) and [`reputation_fixtures.py`](reputation_fixtures.py). The proof uses the Python SDK for Arkiv writes and reads. It demonstrates keeper-paid renewal plus a separate native wallet transfer. Those are distinct from a native separate-fee-payer flow. User-authored records still require the user's own signed transaction.

The proof is intended for a disposable local chain with chain id 1337. It uses published development keys and does not use real funds.
