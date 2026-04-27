# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend-deps
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci

FROM frontend-deps AS frontend-build
WORKDIR /app
COPY frontend ./frontend
RUN npm --prefix frontend run build

FROM node:22-bookworm-slim AS frontend-runtime-deps
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --omit=dev

FROM python:3.13-slim-bookworm AS backend-deps
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN pip install --no-cache-dir uv \
  && uv sync --project backend --frozen --no-dev --no-install-project

FROM python:3.13-slim-bookworm AS runtime
WORKDIR /app

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000 \
    BACKEND_PORT=8000 \
    INTERNAL_BACKEND_API_URL=http://127.0.0.1:8000 \
    PYTHONPATH=/app/backend \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/backend/.venv/bin:$PATH

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates chromium tini \
  && rm -rf /var/lib/apt/lists/*

COPY --from=frontend-deps /usr/local/bin/node /usr/local/bin/node
COPY --from=backend-deps /app/backend/.venv /app/backend/.venv
COPY --from=frontend-build /app/frontend/build /app/frontend/build
COPY --from=frontend-runtime-deps /app/frontend/node_modules /app/frontend/node_modules
COPY frontend/package.json /app/frontend/package.json
COPY backend /app/backend
COPY docker/start.sh /usr/local/bin/start-publicus
RUN chmod +x /usr/local/bin/start-publicus \
  && useradd --create-home --shell /usr/sbin/nologin publicus \
  && chown -R publicus:publicus /app
USER publicus

EXPOSE 3000
ENTRYPOINT ["tini", "--"]
CMD ["start-publicus"]
