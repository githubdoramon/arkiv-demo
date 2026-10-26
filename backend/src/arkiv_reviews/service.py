"""Read one all-pages Arkiv snapshot at a single block through the Python SDK."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from arkiv import Arkiv
from arkiv.query import eq

from .domain import APP_ID

PAGE_SIZE = 200


def _normalise_scalar(value: Any) -> Any:
    # SDK attributes are `Value` objects; payload JSON values are already primitive.
    if hasattr(value, "type") and hasattr(value, "value"):
        value = value.value
    if isinstance(value, str) and re.fullmatch(r"0x[0-9a-fA-F]{40}|0x[0-9a-fA-F]{64}", value):
        return value.lower()
    if isinstance(value, dict):
        return {str(key): _normalise_scalar(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalise_scalar(item) for item in value]
    return value


def _normalise_entity(entity: Any, block_timestamp: Any) -> dict[str, Any]:
    attributes = {
        name: _normalise_scalar(value) for name, value in (entity.attributes or {}).items()
    }
    try:
        payload = entity.to_json()
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        payload = None
    flags = entity.creation_flags
    return {
        "key": str(entity.key).lower(),
        "creator": str(entity.creator).lower(),
        "owner": str(entity.owner).lower(),
        "created_at_block": int(entity.created_at),
        "created_at_timestamp": int(block_timestamp(int(entity.created_at))),
        "expires_at_block": int(entity.expires_at),
        "flags": {
            "readonly": bool(flags.readonly),
            "permissionless_extension": bool(flags.permissionless_extension),
        },
        "attributes": attributes,
        "payload": _normalise_scalar(payload),
    }


def snapshot_from_client(client: Any, *, rpc_url: str) -> dict[str, Any]:
    """SDK test seam: collect all pages while pinning every query to one block number."""
    chain_id = int(client.eth.chain_id)
    block_number = int(client.eth.block_number)
    header = client.eth.get_block(block_number)
    block_timestamp = int(header["timestamp"])
    timestamp_cache: dict[int, int] = {block_number: block_timestamp}

    def get_timestamp(number: int) -> int:
        if number not in timestamp_cache:
            timestamp_cache[number] = int(client.eth.get_block(number)["timestamp"])
        return timestamp_cache[number]

    page = (
        client.select(
            key=True,
            creator=True,
            owner=True,
            created_at=True,
            expires_at=True,
            creation_flags=True,
            attributes=True,
            payload=True,
        )
        .where(eq("app", APP_ID))
        .limit(PAGE_SIZE)
        .at_block(block_number)
        .fetch()
    )
    entities: list[dict[str, Any]] = []
    while True:
        if int(page.block_number) != block_number:
            raise RuntimeError(
                f"Arkiv pagination moved from snapshot block {block_number} to {page.block_number}"
            )
        entities.extend(_normalise_entity(entity, get_timestamp) for entity in page.entities)
        if not page.has_next_page():
            break
        page = page.next()

    return {
        "chain_id": chain_id,
        "block_number": block_number,
        "block_timestamp": block_timestamp,
        "evaluation_day": block_timestamp // 86_400,
        "entities": entities,
    }


class ReviewService:
    """Read-only public service backed by the sibling Arkiv Python SDK."""

    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url
        self.client = Arkiv(rpc_url)
        self.expected_chain_id = int(os.environ['ARKIV_CHAIN_ID']) if os.environ.get('ARKIV_CHAIN_ID') else None

    def health(self) -> dict[str, Any]:
        chain_id = int(self.client.eth.chain_id)
        if self.expected_chain_id is not None and chain_id != self.expected_chain_id:
            raise RuntimeError(f'Expected chain {self.expected_chain_id}; RPC reports {chain_id}.')
        int(self.client.eth.block_number)
        return {"status": "ok", "chain_id": chain_id, "rpc_url": self.rpc_url}

    def snapshot(self) -> dict[str, Any]:
        snapshot = snapshot_from_client(self.client, rpc_url=self.rpc_url)
        if self.expected_chain_id is not None and snapshot['chain_id'] != self.expected_chain_id:
            raise RuntimeError('RPC chain does not match the configured network.')
        return snapshot

    def close(self) -> None:
        self.client.close()
