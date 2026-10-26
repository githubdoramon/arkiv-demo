"""Small read-only API for the review app and independent portfolio demo."""

from __future__ import annotations

import importlib.util
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .domain import validate_snapshot
from .reputation import calculate_scores, events_from_entities
from .service import ReviewService

DEFAULT_RPC_URL = "http://127.0.0.1:18547"
CATALOG_PATH = Path(os.environ.get("ARKIV_CATALOG_PATH", str(Path(__file__).resolve().parents[3] / "shared" / "games.json")))
FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]


def load_catalog(path: Path = CATALOG_PATH) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        catalog = json.load(file)
    if not isinstance(catalog, list):
        raise TypeError("games.json must contain a JSON array")
    return catalog


def _service(request: Request) -> ReviewService:
    service = request.app.state.review_service
    if service is None:
        raise HTTPException(status_code=503, detail="Review RPC client is not configured")
    return service


def create_app(
    *, review_service: Any = None, catalog: list[dict[str, Any]] | None = None
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.review_service is None:
            rpc_url = os.environ.get("ARKIV_RPC_URL", DEFAULT_RPC_URL)
            app.state.review_service = ReviewService(rpc_url)
        try:
            yield
        finally:
            service = app.state.review_service
            if service is not None:
                service.close()

    app = FastAPI(title="Arkiv Reviews", version="0.1.0", lifespan=lifespan)
    app.state.review_service = review_service
    app.state.catalog = catalog if catalog is not None else load_catalog()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=FRONTEND_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/health")
    def health(request: Request) -> Any:
        rpc_url = os.environ.get("ARKIV_RPC_URL", DEFAULT_RPC_URL)
        try:
            return _service(request).health()
        except Exception as exc:  # noqa: BLE001 - health must report any RPC/provider failure
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "chain_id": None,
                    "rpc_url": rpc_url,
                    "error": str(exc),
                },
            )

    @app.get("/api/catalog")
    def get_catalog(request: Request) -> dict[str, Any]:
        return {"games": request.app.state.catalog}

    @app.get("/api/snapshot")
    def get_snapshot(request: Request) -> dict[str, Any]:
        return _service(request).snapshot()

    @app.get("/api/reputation")
    def get_reputation(request: Request) -> dict[str, Any]:
        snapshot = _service(request).snapshot()
        validated = validate_snapshot(snapshot, request.app.state.catalog)
        revisions = {r["key"]: r["payload"]["author"] for r in validated["revisions"]}
        events = events_from_entities(validated["votes"], revisions)
        wallets = (
            {entity["payload"]["wallet"] for entity in validated["profiles"]}
            | {entity["payload"]["author"] for entity in validated["roots"]}
            | {entity["payload"]["voter"] for entity in validated["votes"]}
            | {entity["payload"]["author"] for entity in validated["comments"]}
        )
        scores = calculate_scores(
            events,
            evaluation_day=snapshot["evaluation_day"],
            known_wallets=wallets,
        )
        return {"evaluation_day": snapshot["evaluation_day"], "scores": scores}

    # Moderation is an optional local showcase feature.
    if importlib.util.find_spec("arkiv_reviews.moderation") is not None:
        from .moderation import build_router

        app.include_router(build_router())
    return app


app = create_app()
