"""Private Tiramisu demo accounts. This script prints only public addresses/balances."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from arkiv import Arkiv
from eth_account import Account
from web3 import Web3

CHAIN_ID = 7738577
RPC_URL = 'https://rpc.tiramisu.db-chain.testnet.arkiv.network'
DEFAULT_FILE = Path(__file__).resolve().parents[1] / '.runtime/tiramisu/wallets.json'
ROLES = ('funding', 'author_1', 'author_2', 'author_3', 'keeper')


def load_wallets(path: Path) -> dict:
    data = json.loads(path.read_text())
    if data.get('chain_id') != CHAIN_ID:
        raise ValueError('Wallet file must target Tiramisu.')
    for role in ROLES:
        account = data['accounts'][role]
        if Account.from_key(account['private_key']).address.lower() != account['address'].lower():
            raise ValueError(f'Invalid account for {role}.')
    return data['accounts']


def initialise(path: Path) -> dict:
    if not path.exists():
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        accounts = {}
        for role in ROLES:
            account = Account.create()
            accounts[role] = {'address': account.address, 'private_key': account.key.hex()}
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as file:
            json.dump({'chain_id': CHAIN_ID, 'accounts': accounts}, file, indent=2)
    return load_wallets(path)


def fund_accounts(client: Arkiv, accounts: dict, author_glm: str = '0.1', keeper_glm: str = '0.2') -> int:
    """Top up each recipient to a target balance, confirming each transfer before continuing."""
    if client.eth.chain_id != CHAIN_ID:
        raise ValueError('Refusing to distribute test funds outside Tiramisu.')
    sender = accounts['funding']['address']
    if client.account.address.lower() != sender.lower():
        raise ValueError('Funding signer does not match wallet file.')
    transfers = []
    balance = client.eth.get_balance(sender)
    if balance == 0:
        raise RuntimeError(f'Fund {sender} on Tiramisu before distributing test GLM.')
    gas_price = int(client.eth.gas_price)
    for role in ROLES[1:]:
        target = Web3.to_wei(keeper_glm if role == 'keeper' else author_glm, 'ether')
        address = accounts[role]['address']
        missing = max(0, target - client.eth.get_balance(address))
        if missing:
            gas = client.eth.estimate_gas({'from': sender, 'to': address, 'value': missing})
            transfers.append((role, address, missing, gas))
    total = sum(value + gas * gas_price for _, _, value, gas in transfers)
    balance = client.eth.get_balance(sender)
    if balance < total:
        raise RuntimeError(f'Fund {sender} on Tiramisu first. Balance {Web3.from_wei(balance,"ether")} GLM; distribution needs approximately {Web3.from_wei(total,"ether")} GLM including transfer fees.')
    for role, address, value, gas in transfers:
        transaction = {'chainId': CHAIN_ID, 'nonce': client.eth.get_transaction_count(sender, 'pending'),
                       'to': address, 'value': value, 'gas': gas, 'gasPrice': gas_price}
        signed = client.account.sign_transaction(transaction)
        receipt = client.eth.wait_for_transaction_receipt(client.eth.send_raw_transaction(signed.raw_transaction))
        if receipt.status != 1:
            raise RuntimeError(f'Funding failed for {role}; transaction {receipt.transactionHash.hex()}')
        print(f'Funded {role}: {address}; tx {receipt.transactionHash.hex()}', flush=True)
    return len(transfers)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'status', 'fund', 'export-keeper'])
    parser.add_argument('--wallets-file', type=Path, default=DEFAULT_FILE)
    parser.add_argument('--rpc', default=os.environ.get('ARKIV_RPC_URL', RPC_URL))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    accounts = initialise(args.wallets_file) if args.command == 'init' else load_wallets(args.wallets_file)
    if args.command == 'export-keeper':
        if not args.output:
            parser.error('--output is required for export-keeper')
        args.output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with os.fdopen(os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as file:
            file.write(accounts['keeper']['private_key'] + '\n')
        print(f'Keeper key saved to {args.output}; never include it in an image or public archive.')
        return
    if args.command == 'init':
        for role in ROLES:
            print(f'{role}: {accounts[role]["address"]}')
        return
    with Arkiv(args.rpc, account=accounts['funding']['private_key'] if args.command == 'fund' else None) as client:
        if client.eth.chain_id != CHAIN_ID:
            raise SystemExit('RPC does not report Tiramisu chain 7738577.')
        if args.command == 'fund':
            fund_accounts(client, accounts)
        for role in ROLES:
            address = accounts[role]['address']
            print(f'{role}: {address} — {Web3.from_wei(client.eth.get_balance(address),"ether")} test GLM')


if __name__ == '__main__':
    main()
