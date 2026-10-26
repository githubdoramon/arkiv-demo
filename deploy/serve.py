"""Run the API, static web server and optional keeper within the review container."""
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def main() -> None:
    commands = [
        [sys.executable, '-m', 'uvicorn', 'arkiv_reviews.api:app', '--host', '127.0.0.1', '--port', '8000'],
        ['nginx', '-c', '/etc/sidequest/nginx.conf', '-g', 'daemon off;'],
    ]
    env = dict(os.environ)
    key_file = Path(env.get('ARKIV_KEEPER_KEY_FILE', '/run/sidequest/keeper.key'))
    if key_file.is_file():
        env['ARKIV_KEEPER_PRIVATE_KEY'] = key_file.read_text().strip()
    keeper_enabled = env.get('KEEPER_ENABLED', 'auto')
    if keeper_enabled not in {'auto', '0', '1'}:
        raise SystemExit('KEEPER_ENABLED must be auto, 0 or 1.')
    has_key = bool(env.get('ARKIV_KEEPER_PRIVATE_KEY'))
    if keeper_enabled == '1' and not has_key:
        raise SystemExit('Keeper enabled but no runtime keeper key is configured.')
    if keeper_enabled != '0' and has_key:
        commands.append([sys.executable, 'scripts/renew.py', '--submit', '--watch', '--interval', env.get('ARKIV_KEEPER_INTERVAL', '30')])
        print('Renewal keeper enabled with its runtime key.', flush=True)
    else:
        print('Renewal keeper disabled; mount keeper.key to enable it.', flush=True)
    children = []
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    code = 0
    try:
        for command in commands:
            # Only the keeper receives its private key. API and nginx never need it.
            child_env = env if 'scripts/renew.py' in command else {k: v for k, v in env.items() if k != 'ARKIV_KEEPER_PRIVATE_KEY'}
            children.append(subprocess.Popen(command, env=child_env, start_new_session=True))
        while not stopping:
            if any(child.poll() is not None for child in children):
                print('A service exited; stopping the container so Docker can restart it.', flush=True)
                code = 1
                break
            time.sleep(.5)
    finally:
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
        deadline = time.monotonic() + 10
        for child in children:
            try:
                child.wait(timeout=max(.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
    raise SystemExit(code)


if __name__ == '__main__':
    main()
