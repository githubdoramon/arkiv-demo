# syntax=docker/dockerfile:1
FROM --platform=$BUILDPLATFORM node:24-bookworm-slim AS frontend
WORKDIR /workspace
# Named build contexts copy only SDK source, never caches, credentials or node_modules.
COPY --from=arkiv_js /package.json /workspace/arkiv-sdk-js/package.json
COPY --from=arkiv_js /src /workspace/arkiv-sdk-js/src
COPY frontends /workspace/sidequest/frontends
COPY shared /workspace/sidequest/shared
WORKDIR /workspace/sidequest/frontends
RUN npm ci
ARG REVIEW_APP_URL=https://sidequest.appcalipse.com/
ARG PORTFOLIO_URL=https://portfolios.appcalipse.com/
RUN VITE_REVIEW_APP_URL="$REVIEW_APP_URL" VITE_PORTFOLIO_URL="$PORTFOLIO_URL" npm run build:tiramisu

FROM nginx:stable-alpine AS portfolio
COPY deploy/portfolio.nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend /workspace/sidequest/frontends/portfolio/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1

FROM ghcr.io/astral-sh/uv:0.11.17 AS uv
FROM python:3.13-slim-bookworm AS review-app
COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends nginx ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace/sidequest
COPY --from=arkiv_python /pyproject.toml /workspace/arkiv-python-sdk/pyproject.toml
COPY --from=arkiv_python /README.md /workspace/arkiv-python-sdk/README.md
COPY --from=arkiv_python /src /workspace/arkiv-python-sdk/src
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./backend/
COPY backend/src ./backend/src
RUN --mount=type=cache,target=/root/.cache/uv uv sync --link-mode=copy --frozen --no-dev --no-editable --project backend
COPY shared/games.json ./shared/games.json
COPY scripts/seed.py scripts/testnet_wallets.py scripts/renew.py ./scripts/
COPY deploy/serve.py ./deploy/serve.py
COPY deploy/app.nginx.conf /etc/sidequest/nginx.conf
COPY --from=frontend /workspace/sidequest/frontends/review-app/dist /srv/sidequest
ENV PATH="/workspace/sidequest/backend/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    ARKIV_RPC_URL=https://rpc.tiramisu.db-chain.testnet.arkiv.network \
    ARKIV_CHAIN_ID=7738577 \
    ARKIV_CATALOG_PATH=/workspace/sidequest/shared/games.json \
    ARKIV_MODERATION_DB=/data/moderation.sqlite3 \
    ARKIV_RENEWAL_DB=/data/renewal.sqlite3 \
    ARKIV_KEEPER_KEY_FILE=/run/sidequest/keeper.key
RUN mkdir -p /data /run/sidequest
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz',timeout=4)" || exit 1
CMD ["python", "deploy/serve.py"]
