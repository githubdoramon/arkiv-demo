"""Readiness check for the dedicated local demo node (standard library only)."""

import json
import time
import urllib.request

RPC = "http://127.0.0.1:18547"


def call(method: str) -> str:
    request = urllib.request.Request(
        RPC,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": []}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=1) as response:
        return json.load(response)["result"]


for attempt in range(40):
    try:
        if int(call("eth_chainId"), 16) != 1337:
            raise SystemExit("Demo RPC belongs to another chain; expected local chain 1337.")
        if int(call("eth_blockNumber"), 16) > 0:
            print(f"Local Arkiv ready: {RPC} (chain 1337)")
            break
    except (OSError, ValueError, KeyError):
        pass
    time.sleep(0.5)
else:
    raise SystemExit("Local Arkiv was not ready within 20 seconds.")
