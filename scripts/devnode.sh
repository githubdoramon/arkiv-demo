#!/usr/bin/env bash
set -euo pipefail

image='ghcr.io/arkiv-network/arkiv-reth-dev@sha256:8204268426c2827f136a4fd0f422d61f11f503388df0f70a273c1227b6f6fb4d'
name='arkiv-review-demo'
owner='arkiv-review-demo'
repo="$(cd "$(dirname "$0")/.." && pwd)"
data_dir="$repo/.runtime/node-data"

exists() { docker container inspect "$name" >/dev/null 2>&1; }
check_owner() {
  if [ "$(docker inspect --format '{{ index .Config.Labels "demo.owner" }}' "$name")" != "$owner" ]; then
    echo "Refusing to operate on an unrelated container named $name." >&2
    exit 1
  fi
}

case "${1:-start}" in
  start)
    if exists; then
      check_owner
      docker start "$name"
    else
      mkdir -p "$data_dir"
      docker run --detach --name "$name" --label "demo.owner=$owner" \
        --publish 127.0.0.1:18547:8545 --publish 127.0.0.1:18548:8546 \
        --mount "type=bind,source=$data_dir,target=/data" "$image" \
        node --dev --dev.block-time 250ms --http --http.addr 0.0.0.0 \
        --http.api eth,net,web3,txpool \
        --http.corsdomain 'http://127.0.0.1:5173,http://127.0.0.1:5174,http://localhost:5173,http://localhost:5174' \
        --ws --ws.addr 0.0.0.0 --ws.api eth,net,web3,txpool \
        --ws.origins 'http://127.0.0.1:5173,http://127.0.0.1:5174,http://localhost:5173,http://localhost:5174' \
        --datadir /data
    fi
    python3 "$(dirname "$0")/wait_node.py"
    ;;
  stop)
    if exists; then check_owner; docker stop "$name"; fi
    ;;
  remove)
    if exists; then check_owner; docker rm --force "$name"; fi
    ;;
  logs) check_owner; docker logs --tail 40 "$name" ;;
  *) echo "Usage: bash scripts/devnode.sh start|stop|remove|logs" >&2; exit 2 ;;
esac
