"""Run the Python renewal keeper; dry-run unless --submit is explicit.

Example: uv run --project backend python scripts/renew.py --submit --watch
The built-in funded development keeper is accepted only on loopback chain 1337.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import time
from urllib.parse import urlparse

from arkiv import Arkiv
from arkiv_reviews.renewal import RenewalWorker
from arkiv_reviews.service import ReviewService

REPO = Path(__file__).resolve().parents[1]
# Public Anvil sample key; the chain and loopback checks below limit it to local chain 1337.
DEV_KEEPER = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=5)
    parser.add_argument("--json", action="store_true", help="Print the full target ledger result")
    args = parser.parse_args()
    if args.interval < 1:
        parser.error("--interval must be at least one second")
    rpc_url = os.environ.get("ARKIV_RPC_URL", "http://127.0.0.1:18547")
    with Arkiv(rpc_url) as probe:
        chain_id = probe.eth.chain_id
    keeper_key = os.environ.get("ARKIV_KEEPER_PRIVATE_KEY")
    if args.submit and not keeper_key:
        if urlparse(rpc_url).hostname not in {"127.0.0.1", "localhost", "::1"} or chain_id != 1337:
            raise SystemExit("Configure ARKIV_KEEPER_PRIVATE_KEY explicitly outside the local demo.")
        keeper_key = DEV_KEEPER
    worker = RenewalWorker(
        rpc_url=rpc_url,
        keeper_key=keeper_key,
        state_path=os.environ.get("ARKIV_RENEWAL_DB", str(REPO / ".runtime/renewal.sqlite3")),
    )
    service = ReviewService(rpc_url)
    try:
        while True:
            try:
                result = worker.run_once(service.snapshot(), dry_run=not args.submit)
            except Exception as exc:
                if not args.watch:
                    raise
                print(f"Keeper: RPC temporarily unavailable; retrying: {exc}", flush=True)
                time.sleep(args.interval)
                continue
            if result.get("targets") or not args.watch:
                if args.json:
                    print(json.dumps(result, default=str), flush=True)
                else:
                    statuses = dict(Counter(row["status"] for row in result.get("targets", [])))
                    print(f"Keeper: {result.get('credit_count', 0)} new credits; {statuses or 'no pending renewals'}", flush=True)
            if not args.watch:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        if hasattr(service, "close"):
            service.close()


if __name__ == "__main__":
    main()
