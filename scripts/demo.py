"""One command to set up, seed and serve the complete local showcase.

Run from the repository root: python3 scripts/demo.py [--skip-install] [--no-seed].
Ctrl-C stops only the servers started here. The local chain remains for the next session;
stop or remove it explicitly with scripts/devnode.sh.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import subprocess
import time

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
FRONTENDS = REPO / "frontends"


def run(*args: str) -> None:
    subprocess.run(args, cwd=REPO, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--no-seed", action="store_true")
    args = parser.parse_args()
    if not args.skip_install:
        run("uv", "sync", "--project", str(BACKEND))
        run("npm", "--prefix", str(FRONTENDS), "ci")
    run("bash", str(REPO / "scripts/devnode.sh"), "start")
    if not args.no_seed:
        run("uv", "run", "--project", str(BACKEND), "python", str(REPO / "scripts/seed.py"))
    env = {
        **os.environ,
        "ARKIV_RPC_URL": "http://127.0.0.1:18547",
        "ARKIV_MODERATION_DB": str(REPO / ".runtime/moderation.sqlite3"),
        "ARKIV_RENEWAL_DB": str(REPO / ".runtime/renewal.sqlite3"),
    }
    commands = [
        ["uv", "run", "--project", str(BACKEND), "uvicorn", "arkiv_reviews.api:app", "--host", "127.0.0.1", "--port", "8000"],
        ["npm", "--prefix", str(FRONTENDS), "run", "dev:review"],
        ["npm", "--prefix", str(FRONTENDS), "run", "dev:portfolio"],
        ["uv", "run", "--project", str(BACKEND), "python", str(REPO / "scripts/renew.py"), "--submit", "--watch"],
    ]
    children: list[subprocess.Popen] = []
    try:
        for command in commands:
            children.append(subprocess.Popen(command, cwd=REPO, env=env, start_new_session=True))
        print("\nSidequest demo starting:", flush=True)
        print("  Reviews:   http://127.0.0.1:5173", flush=True)
        print("  Portfolio: http://127.0.0.1:5174", flush=True)
        print("  Python API: http://127.0.0.1:8000/docs", flush=True)
        print("  Keeper: watching local activity and paying earned renewals", flush=True)
        print("Ctrl-C stops the servers and keeper; local chain data is retained.\n", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.5)
        raise SystemExit("A demo server exited; inspect its output above.")
    except KeyboardInterrupt:
        print("\nStopping demo servers…", flush=True)
    finally:
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)


if __name__ == "__main__":
    main()
