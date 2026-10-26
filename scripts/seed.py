"""Write a small, repeatable set of real demo records through our Python SDK.

Defaults to loopback chain 1337. Explicit --network tiramisu uses private accounts
from --wallets-file. Existing creator-verified records are reused instead of duplicated.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, uuid5

from arkiv import Arkiv, CreationFlags, ExpirationTime, json_to_payload
from arkiv.query import eq
from eth_account import Account
from web3 import Web3
from testnet_wallets import CHAIN_ID, RPC_URL, DEFAULT_FILE, load_wallets, fund_accounts

CODE_ROOT = Path(__file__).resolve().parents[1]
RPC = os.environ.get("ARKIV_RPC_URL", "http://127.0.0.1:18547")
APP = "arkiv-review-demo"
FLAGS = CreationFlags(readonly=True, permissionless_extension=True)
DEV_KEYS = [
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
    Web3.keccak(text="sidequest-local-demo-reader-three").hex(),
]
PEOPLE = [
    ("Alex Morgan", "Exploration, small details, and games that respect your time."),
    ("Jamie Chen", "Looking for great systems and one-more-run energy."),
    ("Sam Rivera", "Stories worth finishing. Usually playing on a handheld."),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network', choices=['local', 'tiramisu'], default='local')
    parser.add_argument('--wallets-file', type=Path, default=DEFAULT_FILE)
    args = parser.parse_args()
    rpc = os.environ.get('ARKIV_RPC_URL', RPC_URL if args.network == 'tiramisu' else RPC)
    chain_id = CHAIN_ID if args.network == 'tiramisu' else 1337
    if args.network == 'local' and urlparse(rpc).hostname not in {'localhost', '127.0.0.1', '::1'}:
        raise SystemExit('Local seed refuses non-loopback RPC URLs.')
    with Arkiv(rpc) as probe:
        if probe.eth.chain_id != chain_id:
            raise SystemExit(f'Seed expected chain {chain_id}; RPC reports {probe.eth.chain_id}.')
    if args.network == 'tiramisu':
        accounts = load_wallets(args.wallets_file)
        with Arkiv(rpc, account=accounts['funding']['private_key']) as funding:
            fund_accounts(funding, accounts)
        keys = [accounts[f'author_{index}']['private_key'] for index in range(1, 4)]
    else:
        keys = DEV_KEYS
    catalog = json.loads((CODE_ROOT / "shared/games.json").read_text())
    if isinstance(catalog, dict):
        catalog = catalog["games"]
    clients = [Arkiv(rpc, account=key) for key in keys]
    try:
        primary = clients[0]
        for recipient in (clients[1:] if args.network == 'local' else []):
            if primary.eth.get_balance(recipient.account.address) < 10**17:
                transaction = {
                    "chainId": chain_id,
                    "nonce": primary.eth.get_transaction_count(primary.account.address, "pending"),
                    "to": recipient.account.address,
                    "value": 10**18,
                    "gas": 21000,
                    "gasPrice": primary.eth.gas_price,
                }
                signed = primary.account.sign_transaction(transaction)
                receipt = primary.eth.wait_for_transaction_receipt(
                    primary.eth.send_raw_transaction(signed.raw_transaction)
                )
                if receipt.status != 1:
                    raise RuntimeError("Local development wallet funding failed.")

        existing: dict[tuple[str, str], str] = {}
        page = primary.query(eq("app", APP), limit=200)
        while True:
            for entity in page.entities:
                try:
                    body = entity.to_json()
                    logical_id = body.get("logical_id")
                    if logical_id:
                        existing.setdefault((str(entity.creator).lower(), logical_id), entity.key)
                except (ValueError, AttributeError):
                    continue
            if not page.has_next_page():
                break
            page = page.next()

        created = 0

        def publish(client: Arkiv, kind: str, body: dict, attrs: dict) -> str:
            nonlocal created
            logical_id = body["logical_id"]
            identity = (client.account.address.lower(), logical_id)
            if identity in existing:
                return existing[identity]
            result = client.create_entity(
                payload=json_to_payload(body),
                content_type="application/json",
                attributes={"app": APP, "kind": kind, "logical_id": logical_id, **attrs},
                expires=ExpirationTime.from_days(180),
                flags=CreationFlags(permissionless_extension=True) if kind == "profile" else FLAGS,
            )
            existing[identity] = result.entity_key
            created += 1
            return result.entity_key

        for index, client in enumerate(clients):
            wallet = client.account.address.lower()
            publish(client, "profile", {
                "schema": "profile/v1", "wallet": wallet,
                "display_name": PEOPLE[index][0], "bio": PEOPLE[index][1],
                "logical_id": f"profile:{chain_id}:{wallet}",
            }, {"wallet": wallet})

        review_keys: list[tuple[int, str, str]] = []
        excerpts = [
            "The strongest moments are the quiet ones. I kept taking the long way around just to see what I might discover. A few rough edges, but the sense of place stayed with me long after the credits.",
            "A lovely balance of readable systems and room to experiment. It rewards paying attention rather than grinding. I wish the early tutorial trusted the player a little more, but it quickly finds its rhythm.",
            "This works beautifully in short sessions. The controls feel considered and the pace rarely drags. The middle section repeats itself a little; the final stretch earns its place.",
        ]
        for game_index, game in enumerate(catalog[:4]):
            for person_index in range(2):
                client_index = (game_index + person_index) % len(clients)
                client = clients[client_index]
                author = client.account.address.lower()
                platforms = game["platforms"]
                platform = platforms[person_index % len(platforms)]
                root_id = f"review:{chain_id}:{author}:{game['id']}:{platform}"
                root_key = publish(client, "review-root", {
                    "schema": "review-root/v1", "author": author,
                    "game_id": game["id"], "platform": platform, "logical_id": root_id,
                }, {"author": author, "game_id": game["id"], "platform": platform})
                revision_key = publish(client, "review-revision", {
                    "schema": "review-revision/v1", "root_key": root_key,
                    "revision": 1, "previous_revision_key": None,
                    "author": author, "rating_half_stars": [9, 8, 7][client_index],
                    "text": excerpts[client_index], "logical_id": f"{root_key}:revision:1",
                }, {"root_key": root_key, "revision": 1})
                review_keys.append((client_index, root_key, revision_key))

        for review_index, (owner_index, _root_key, revision_key) in enumerate(review_keys):
            voter_index = (owner_index + 1) % len(clients)
            voter = clients[voter_index]
            wallet = voter.account.address.lower()
            publish(voter, "review-vote", {
                "schema": "review-vote/v1", "target_revision_key": revision_key,
                "voter": wallet, "value": "helpful",
                "logical_id": f"vote:{revision_key}:{wallet}",
            }, {"target_revision_key": revision_key, "voter": wallet})
            if review_index < 3:
                publish(voter, "review-comment", {
                    "schema": "review-comment/v1", "target_revision_key": revision_key,
                    "author": wallet, "text": "This is useful context. How did it feel in shorter sessions?",
                    "logical_id": f"comment:{uuid5(NAMESPACE_URL, 'sidequest-seed-' + revision_key)}",
                }, {"target_revision_key": revision_key, "author": wallet})

        print(f"Network: {args.network} ({chain_id})")
        print(f"Seed complete: {created} new entities; {len(review_keys)} demo reviews.")
        print("All demo reviews were written through the Python SDK.")
        print("Demo authors:")
        for index, client in enumerate(clients):
            print(f"  {PEOPLE[index][0]}: {client.account.address}")
    finally:
        for client in clients:
            client.close()


if __name__ == "__main__":
    main()
