"""Local showcase moderation queue; Arkiv remains the review/reputation source."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

KEY_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
REASONS = {"spam", "abuse", "off_topic", "other"}


class ReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reporter: str = Field(min_length=42, max_length=42)
    entity_key: str = Field(min_length=66, max_length=66)
    reason: str = Field(min_length=1, max_length=20)
    details: str = Field(default="", max_length=300)
    signature: str = Field(min_length=130, max_length=132)


class HideInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hidden: bool
    reason: str = Field(min_length=1, max_length=200)


def report_message(reporter: str, entity_key: str, reason: str, details: str = "") -> str:
    """Canonical EIP-191 text; clients must sign these normalized values."""
    return ("Arkiv review report\n"
            f"reporter:{reporter.lower()}\n"
            f"entity_key:{entity_key.lower()}\n"
            f"reason:{reason}\n"
            f"details:{details.strip()}")


def build_router(*, db_path: str | Path | None = None, moderator_token: str | None = None) -> APIRouter:
    """Build routes with an ignored local SQLite queue and optional test seams."""
    path = Path(db_path or os.getenv("ARKIV_MODERATION_DB", "./runtime/moderation.sqlite3"))
    token = moderator_token if moderator_token is not None else os.getenv("MODERATOR_TOKEN", "")

    def connect():
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path, timeout=10)
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
          CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY, reporter TEXT NOT NULL,
            entity_key TEXT NOT NULL, reason TEXT NOT NULL, details TEXT NOT NULL,
            created_at INTEGER NOT NULL, ip_hash TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS hidden(entity_key TEXT PRIMARY KEY, reason TEXT NOT NULL,
            updated_at INTEGER NOT NULL);
        """)
        return db

    router = APIRouter(prefix="/api", tags=["moderation"])

    @router.post("/reports", status_code=201)
    def submit_report(body: ReportInput, request: Request):
        reporter, key = body.reporter.lower(), body.entity_key.lower()
        details = body.details.strip()
        if not ADDR_RE.fullmatch(body.reporter) or not KEY_RE.fullmatch(body.entity_key):
            raise HTTPException(422, "Invalid reporter or entity key")
        if body.reason not in REASONS:
            raise HTTPException(422, "Unknown report reason")
        if "\x00" in details:
            raise HTTPException(422, "Invalid details")
        try:
            recovered = Account.recover_message(
                encode_defunct(text=report_message(reporter, key, body.reason, details)),
                signature=body.signature,
            ).lower()
        except Exception as exc:
            raise HTTPException(422, "Invalid wallet signature") from exc
        if recovered != reporter:
            raise HTTPException(401, "Signature does not match reporter")
        now = int(time.time())
        peer = request.client.host if request.client else "unknown"
        ip_hash = hashlib.sha256(peer.encode()).hexdigest()
        with connect() as db:
            # Showcase-level limits: 5 reports per wallet and 20 per network per hour.
            wallet_count = db.execute("SELECT COUNT(*) FROM reports WHERE reporter=? AND created_at>?",
                                      (reporter, now - 3600)).fetchone()[0]
            ip_count = db.execute("SELECT COUNT(*) FROM reports WHERE ip_hash=? AND created_at>?",
                                  (ip_hash, now - 3600)).fetchone()[0]
            if wallet_count >= 5 or ip_count >= 20:
                raise HTTPException(429, "Report rate limit reached")
            report_id = secrets.token_hex(16)
            db.execute("INSERT INTO reports VALUES(?,?,?,?,?,?,?)",
                       (report_id, reporter, key, body.reason, details, now, ip_hash))
        return {"report_id": report_id}

    @router.get("/moderation")
    def get_hidden():
        with connect() as db:
            keys = [row[0] for row in db.execute("SELECT entity_key FROM hidden ORDER BY entity_key")]
        return {"hidden_keys": keys}

    @router.put("/moderation/{entity_key}")
    def set_hidden(entity_key: str, body: HideInput, authorization: str | None = Header(default=None)):
        if not token:
            raise HTTPException(503, "Moderation operator is not configured")
        supplied = authorization.removeprefix("Bearer ") if authorization else ""
        if not hmac.compare_digest(supplied, token):
            raise HTTPException(401, "Operator authentication required")
        if not KEY_RE.fullmatch(entity_key):
            raise HTTPException(422, "Invalid entity key")
        key = entity_key.lower()
        with connect() as db:
            if body.hidden:
                db.execute("INSERT INTO hidden VALUES(?,?,?) ON CONFLICT(entity_key) DO UPDATE SET reason=excluded.reason, updated_at=excluded.updated_at",
                           (key, body.reason.strip(), int(time.time())))
            else:
                db.execute("DELETE FROM hidden WHERE entity_key=?", (key,))
        return {"entity_key": key, "hidden": body.hidden}

    return router
