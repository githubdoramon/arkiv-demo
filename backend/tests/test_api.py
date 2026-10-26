from __future__ import annotations

import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient

from arkiv_reviews.api import create_app

REPO = Path(__file__).resolve().parents[2]
GAMES = json.loads((REPO / "shared" / "games.json").read_text())
FIXTURE = json.loads((REPO / "shared" / "reputation-fixtures.json").read_text())


class FakeService:
    rpc_url = "http://local.test"

    def health(self):
        return {"status": "ok", "chain_id": 1337, "rpc_url": self.rpc_url}

    def snapshot(self):
        return {
            "chain_id": FIXTURE["chain_id"],
            "block_number": 20,
            "block_timestamp": FIXTURE["evaluation_day"] * 86_400,
            "evaluation_day": FIXTURE["evaluation_day"],
            "entities": copy.deepcopy(FIXTURE["entities"]),
        }

    def close(self):
        pass


def test_core_routes_match_contract() -> None:
    with TestClient(create_app(review_service=FakeService(), catalog=GAMES)) as client:
        health = client.get("/api/health")
        catalog = client.get("/api/catalog")
        snapshot = client.get("/api/snapshot")
        reputation = client.get("/api/reputation")

    assert health.json() == {"status": "ok", "chain_id": 1337, "rpc_url": "http://local.test"}
    assert len(catalog.json()["games"]) == 20
    assert set(snapshot.json()) == {
        "chain_id",
        "block_number",
        "block_timestamp",
        "evaluation_day",
        "entities",
    }
    assert set(snapshot.json()["entities"][0]) == {
        "key",
        "creator",
        "owner",
        "created_at_block",
        "created_at_timestamp",
        "expires_at_block",
        "flags",
        "attributes",
        "payload",
    }
    assert reputation.json()["evaluation_day"] == FIXTURE["evaluation_day"]
    assert reputation.json()["scores"]["0x0000000000000000000000000000000000000001"] == 0.002


def test_health_reports_rpc_failure() -> None:
    class BrokenService(FakeService):
        def health(self):
            raise OSError("node unavailable")

    with TestClient(create_app(review_service=BrokenService(), catalog=GAMES)) as client:
        response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json()["status"] == "error"
    assert response.json()["error"] == "node unavailable"
