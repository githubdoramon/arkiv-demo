from pathlib import Path
import importlib.util
import json
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/testnet_wallets.py'
spec = importlib.util.spec_from_file_location('testnet_wallets', SCRIPT)
wallets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wallets)


def test_private_wallets_are_stable_and_validate_identity(tmp_path):
    path = tmp_path / 'wallets.json'
    first = wallets.initialise(path)
    assert wallets.initialise(path) == first
    assert path.stat().st_mode & 0o777 == 0o600
    assert len({item['address'] for item in first.values()}) == 5
    data = json.loads(path.read_text())
    data['accounts']['funding']['address'] = data['accounts']['keeper']['address']
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='Invalid account'):
        wallets.load_wallets(path)


def test_funding_refuses_wrong_chain_and_empty_source(tmp_path):
    accounts = wallets.initialise(tmp_path / 'wallets.json')
    client = SimpleNamespace(eth=SimpleNamespace(chain_id=1337))
    with pytest.raises(ValueError, match='outside Tiramisu'):
        wallets.fund_accounts(client, accounts)
    client.eth = SimpleNamespace(chain_id=wallets.CHAIN_ID, get_balance=lambda _: 0)
    client.account = SimpleNamespace(address=accounts['funding']['address'])
    with pytest.raises(RuntimeError, match='Fund .* on Tiramisu'):
        wallets.fund_accounts(client, accounts)


def test_funded_recipients_do_not_trigger_transfers(tmp_path):
    accounts = wallets.initialise(tmp_path / 'wallets.json')
    client = SimpleNamespace(
        account=SimpleNamespace(address=accounts['funding']['address']),
        eth=SimpleNamespace(chain_id=wallets.CHAIN_ID, gas_price=1, get_balance=lambda _: 10**18),
    )
    assert wallets.fund_accounts(client, accounts) == 0
