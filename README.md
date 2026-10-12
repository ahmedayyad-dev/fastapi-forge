# fastapi-forge

> A production-ready, asynchronous **FastAPI** template with a clean layered
> architecture, Redis-backed caching, rate limiting and distributed locks,
> structured JSON logging and a full Docker + CI setup.

[![CI](https://github.com/ahmedayyad-dev/fastapi-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/ahmedayyad-dev/fastapi-forge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

---

## Features

- **Layered architecture** — `api / core / services / repos / schemas`, so business
  logic never leaks into the transport or persistence layers.
- **Typed configuration** with `pydantic-settings` (`FORGE_` env prefix, `.env` support).
- **Redis (async, `redis.asyncio`)** used for three distinct concerns:
  - **Caching** — namespaced JSON cache with TTL and read-through helper.
  - **Rate limiting** — atomic sliding-window algorithm implemented in a Lua script.
  - **Distributed lock** — `SET NX PX` ownership token with a compare-and-delete Lua release.
- **Middleware** — request-id propagation (`X-Request-ID`) plus one structured JSON
  access-log line per request (`python-json-logger`).
- **Health checks** — `/health/live` and `/health/ready` (Redis-aware), wired into
  Docker `HEALTHCHECK`.
- **Consistent error envelope** for domain errors and validation failures.
- **Multi-stage Dockerfile** (uv builder → slim, non-root runtime) and a
  `docker-compose.yml` with `app + redis`, healthchecks and volumes.
- **Tests** with `pytest`, `fakeredis` and `httpx.AsyncClient` — no external services needed.
- **Quality gates**: Ruff (lint + format), mypy (strict), pre-commit and GitHub Actions CI.

## Tech stack

`Python 3.12` · `FastAPI` · `uvicorn` · `pydantic` v2 · `redis.asyncio` · `uv` · `Docker`

---

## Quickstart

### Option A — Local (uv)

```bash
# 1. Install dependencies (creates .venv)
uv sync --extra dev

# 2. Start Redis (any way you like)
docker run --rm -p 6379:6379 redis:7-alpine

# 3. Configure
cp .env.example .env

# 4. Run
uv run uvicorn fastapi_forge.main:app --reload
```

API docs: http://localhost:8000/docs · ReDoc: http://localhost:8000/redoc

### Option B — Docker Compose (app + redis)

```bash
docker compose up --build
```

The app waits for a healthy Redis (`depends_on: condition: service_healthy`) and
exposes http://localhost:8000.

---

## Project layout

```
fastapi-forge/
├── src/fastapi_forge/
│   ├── main.py                # application factory + lifespan
│   ├── api/
│   │   ├── deps.py            # dependency wiring (DI)
│   │   └── v1/
│   │       ├── router.py      # aggregate v1 router
│   │       └── endpoints/     # health.py, items.py
│   ├── core/
│   │   ├── config.py          # pydantic-settings
│   │   ├── logging.py         # JSON logging + request-id filter
│   │   ├── middleware.py      # request-id + access log (pure ASGI)
│   │   ├── redis.py           # connection pool / client factories
│   │   ├── cache.py           # JSON cache facade
│   │   ├── rate_limit.py      # sliding-window limiter (Lua)
│   │   ├── lock.py            # distributed lock (Lua release)
│   │   └── exceptions.py      # domain errors + handlers
│   ├── services/              # business logic
│   ├── repos/                 # data access (protocol + in-memory impl)
│   └── schemas/               # pydantic request/response models
├── tests/                     # pytest suite (fakeredis + httpx)
├── Dockerfile                 # multi-stage build
├── docker-compose.yml         # app + redis
└── .github/workflows/ci.yml   # lint, type-check, tests
```

## Configuration

All settings are overridable via environment variables with the `FORGE_` prefix.

| Variable | Default | Description |
| --- | --- | --- |
| `FORGE_ENVIRONMENT` | `local` | `local` / `staging` / `production` |
| `FORGE_DEBUG` | `false` | FastAPI debug mode |
| `FORGE_API_V1_PREFIX` | `/api/v1` | Base path for the v1 API |
| `FORGE_REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `FORGE_REDIS_MAX_CONNECTIONS` | `20` | Pool size |
| `FORGE_CACHE_TTL_SECONDS` | `60` | Default cache TTL |
| `FORGE_RATE_LIMIT_REQUESTS` | `100` | Requests allowed per window |
| `FORGE_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate-limit window length |
| `FORGE_LOCK_TTL_SECONDS` | `30` | Default distributed-lock TTL |
| `FORGE_LOCK_BLOCKING_TIMEOUT_SECONDS` | `5.0` | Max wait for a lock |
| `FORGE_LOG_LEVEL` | `INFO` | Root log level |
| `FORGE_LOG_JSON` | `true` | JSON (true) vs. plain text (false) logs |
| `FORGE_REQUEST_ID_HEADER` | `X-Request-ID` | Correlation header name |
| `FORGE_CORS_ORIGINS` | *(empty)* | Comma-separated list, JSON list or `*` |

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health/live` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe (pings Redis) |
| `POST` | `/api/v1/items` | Create an item |
| `GET` | `/api/v1/items` | List items (paginated) |
| `GET` | `/api/v1/items/{id}` | Fetch an item (cached) |
| `PATCH` | `/api/v1/items/{id}` | Update an item |
| `DELETE` | `/api/v1/items/{id}` | Delete an item |

Errors share a single envelope:

```json
{
  "error": {
    "code": "not_found",
    "message": "Item ... does not exist",
    "request_id": "6f1c0a2b..."
  }
}
```

## Using the Redis primitives

```python
from fastapi_forge.core.cache import Cache
from fastapi_forge.core.lock import RedisLock
from fastapi_forge.core.rate_limit import RateLimiter

cache = Cache(redis, default_ttl=60)
await cache.set("key", {"value": 1})
await cache.get_or_set("expensive", compute, ttl=30)

limiter = RateLimiter(redis, limit=10, window_seconds=60)
if not (await limiter.check("user:42")).allowed:
    ...

async with RedisLock(redis, "orders:42", ttl=30):
    ...  # critical section, safe across processes
```

## Tests

```bash
uv run pytest                    # run the suite
uv run pytest --cov=fastapi_forge --cov-report=term-missing
```

The suite uses `fakeredis` and `httpx.ASGITransport`, so it runs without a real
Redis or HTTP server.

## Quality checks

```bash
uv run ruff check .              # lint
uv run ruff format --check .     # formatting
uv run mypy src                  # static typing
```

Or via the `Makefile`: `make check` runs lint, typecheck and tests together.

## License

Released under the [MIT License](LICENSE).
