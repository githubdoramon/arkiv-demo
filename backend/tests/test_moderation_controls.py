from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from eth_account import Account
from eth_account.messages import encode_defunct

from arkiv_reviews.moderation import build_router, report_message


def test_signed_report_and_operator_hide_unhide(tmp_path):
    account = Account.create()
    entity_key = "0x" + "ab" * 32
    reason, details = "spam", "Repeated promotional content"
    message = report_message(account.address, entity_key, reason, details)
    signature = Account.sign_message(encode_defunct(text=message), account.key).signature.hex()

    app = FastAPI()
    app.include_router(build_router(db_path=tmp_path / "moderation.sqlite", moderator_token="operator-secret"))
    client = TestClient(app)
    report = client.post("/api/reports", json={"reporter": account.address, "entity_key": entity_key,
                                               "reason": reason, "details": details,
                                               "signature": signature})
    assert report.status_code == 201
    assert report.json()["report_id"]
    assert client.get("/api/moderation").json() == {"hidden_keys": []}

    denied = client.put(f"/api/moderation/{entity_key}", json={"hidden": True, "reason": "review"})
    assert denied.status_code == 401
    hidden = client.put(f"/api/moderation/{entity_key}",
                        headers={"Authorization": "Bearer operator-secret"},
                        json={"hidden": True, "reason": "queued for review"})
    assert hidden.status_code == 200 and hidden.json()["hidden"] is True
    assert client.get("/api/moderation").json() == {"hidden_keys": [entity_key]}
    unhidden = client.put(f"/api/moderation/{entity_key}",
                          headers={"Authorization": "Bearer operator-secret"},
                          json={"hidden": False, "reason": "cleared"})
    assert unhidden.status_code == 200
    assert client.get("/api/moderation").json() == {"hidden_keys": []}


def test_report_rejects_changed_signed_fields(tmp_path):
    account = Account.create()
    entity_key = "0x" + "ab" * 32
    signature = Account.sign_message(encode_defunct(text=report_message(
        account.address, entity_key, "spam", "")), account.key).signature.hex()
    app = FastAPI()
    app.include_router(build_router(db_path=tmp_path / "moderation.sqlite", moderator_token="token"))
    response = TestClient(app).post("/api/reports", json={"reporter": account.address,
        "entity_key": entity_key, "reason": "abuse", "signature": signature})
    assert response.status_code == 401
