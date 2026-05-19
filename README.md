# FastAPI Boilerplate

A production-grade FastAPI starter, built around modern Python 3.13 idioms and the current best-of-breed toolchain.

> Batteries included: async SQLAlchemy 2.0, Pydantic v2, structured logging, RFC 7807 errors, layered architecture, full test setup, multi-stage Docker, GitHub Actions, pre-commit, and `uv` for dependency management.

---

## Table of contents

1. [Features](#features)
2. [Tech stack](#tech-stack)
3. [Project layout](#project-layout)
4. [Quick start](#quick-start)
5. [Configuration](#configuration)
6. [Development workflow](#development-workflow)
7. [Database migrations](#database-migrations)
8. [Testing](#testing)
9. [Code quality](#code-quality)
10. [Docker](#docker)
11. [Production deployment](#production-deployment)
12. [Architecture](#architecture)
13. [Adding a new resource](#adding-a-new-resource)
14. [API conventions](#api-conventions)
15. [License](#license)

---

## Features

- **FastAPI 0.115+** with the latest `Annotated[..., Depends(...)]` dependency idioms.
- **Async SQLAlchemy 2.0** ORM with typed `Mapped[...]` columns and `asyncpg` driver.
- **Pydantic v2** for schemas and `pydantic-settings` for environment-validated configuration.
- **Layered architecture** — `api → services → repositories → models` — so business logic stays out of HTTP handlers.
- **Versioned API** under `/api/v1`, ready to grow into `/v2` without breaking clients.
- **RFC 7807 Problem Details** error responses through a global exception hierarchy.
- **Structured logging** with `structlog`, request IDs propagated via `contextvars`, JSON output in production.
- **Generic `BaseRepository`** for CRUD plumbing, plus domain-specific repositories for richer queries.
- **Alembic** wired for async migrations and the `src/` layout, with auto-formatting hooks.
- **Pytest + httpx + ASGI lifespan** test harness against an in-memory SQLite database.
- **`uv`** for dependency resolution, locking, and a fast venv-less workflow.
- **Ruff** (lint + format) and **mypy --strict** enforced locally and in CI.
- **Pre-commit hooks** that match CI — no surprise failures on push.
- **Multi-stage Dockerfile** with non-root user and healthcheck; **docker compose** with Postgres healthcheck.
- **GitHub Actions CI** running lint, type check, tests, and a Docker build.

---

## Tech stack

| Concern               | Choice                                      |
| --------------------- | ------------------------------------------- |
| Language              | Python **3.13**                             |
| Web framework         | **FastAPI** ≥ 0.115                         |
| ASGI server           | **Uvicorn** (standard)                      |
| ORM                   | **SQLAlchemy 2.0** (async)                  |
| Database driver       | **asyncpg**                                 |
| Migrations            | **Alembic** (async env)                     |
| Validation / settings | **Pydantic v2** + **pydantic-settings**     |
| Logging               | **structlog**                               |
| Package manager       | **uv** (replaces pip / poetry / pipenv)     |
| Lint + format         | **Ruff**                                    |
| Type checker          | **mypy** (strict mode)                      |
| Tests                 | **pytest**, **pytest-asyncio**, **httpx**   |
| Container             | Multi-stage **Docker** image on Python 3.13 |

---

## Project layout

```
fastapi-boilerplate/
├── .github/workflows/ci.yml      # Lint, type check, test, Docker build
├── alembic/
│   ├── env.py                    # Async migration environment, src-aware
│   ├── script.py.mako            # Modern Python 3.13 migration template
│   └── versions/                 # Generated revision files
├── src/
│   └── app/
│       ├── main.py               # FastAPI app factory + ASGI export
│       ├── api/
│       │   ├── deps.py           # Reusable Annotated[Depends(...)] aliases
│       │   ├── router.py         # Top-level /api router
│       │   └── v1/
│       │       ├── router.py     # v1 sub-router aggregator
│       │       └── endpoints/    # health.py, users.py, …
│       ├── core/
│       │   ├── config.py         # pydantic-settings Settings class
│       │   ├── logging.py        # structlog configuration
│       │   ├── exceptions.py     # AppException hierarchy
│       │   ├── exception_handlers.py  # FastAPI handlers → ProblemDetail
│       │   ├── middleware.py     # Request-id / access-log middleware
│       │   └── lifespan.py       # Startup/shutdown lifecycle
│       ├── db/
│       │   ├── base.py           # DeclarativeBase + naming convention
│       │   ├── mixins.py         # TimestampMixin
│       │   └── session.py        # Async engine + sessionmaker + get_session
│       ├── models/               # SQLAlchemy ORM models
│       ├── repositories/         # Data access (CRUD + queries)
│       ├── schemas/              # Pydantic v2 request/response models
│       └── services/             # Business logic
├── tests/
│   ├── conftest.py               # AsyncClient + ephemeral DB fixtures
│   ├── unit/                     # Fast, isolated tests
│   └── integration/              # End-to-end tests against the ASGI app
├── .env.example                  # Documented environment variables
├── .pre-commit-config.yaml
├── .python-version               # 3.13
├── Dockerfile                    # Multi-stage build with uv
├── docker-compose.yml            # API + Postgres with healthchecks
├── Makefile                      # Common developer commands
├── alembic.ini
├── pyproject.toml                # Single source of truth for tooling
└── README.md
```

---

## Quick start

### Prerequisites

- **Docker** (for the bundled Postgres) — everything else is installed by `make setup`.
- Optional: a system Python ≥ 3.11 to bootstrap `uv` (any modern distro qualifies).

### One-command bootstrap

```bash
git clone <your-repo-url>
cd fastapi-boilerplate

make setup       # installs uv + Python 3.13, creates .env, starts Postgres, installs deps, runs migrations
make dev         # auto-reload server on http://localhost:8000
```

`make setup` is idempotent — safe to re-run any time. Under the hood it composes these granular targets, each of which you can call on its own:

| Target        | What it does                                                                  |
| ------------- | ----------------------------------------------------------------------------- |
| `setup-uv`    | Installs `uv` if missing, then pins Python 3.13 via `uv python install 3.13`. |
| `setup-env`   | Copies `.env.example` → `.env` if `.env` is absent.                           |
| `install`     | `uv sync --all-extras` — resolves and installs everything into `.venv`.       |
| `setup-db`    | Starts the Postgres service via `docker compose up -d db`.                    |
| `wait-db`     | Polls `pg_isready` until the container is accepting connections.              |
| `migrate`     | `alembic upgrade head`.                                                       |
| `reset`       | **Destructive.** Wipes the Postgres volume and re-runs `setup`.               |
| `doctor`      | Prints versions of `uv`, Python, Docker, and Make — useful for bug reports.   |

### Manual setup (if you'd rather wire it yourself)

```bash
git clone <your-repo-url>
cd fastapi-boilerplate

# 1. uv + Python
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.13

# 2. Dependencies
uv sync --all-extras

# 3. Environment
cp .env.example .env
$EDITOR .env

# 4. Postgres (or point .env at an existing instance)
docker compose up -d db

# 5. Migrations + run
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The API is now live at <http://localhost:8000>:

- Swagger UI → <http://localhost:8000/docs>
- ReDoc      → <http://localhost:8000/redoc>
- OpenAPI    → <http://localhost:8000/api/openapi.json>
- Health     → <http://localhost:8000/api/v1/health>

### Run the full stack with one command

```bash
docker compose up --build
```

This starts Postgres and the API with healthchecks. Migrations run automatically against the configured DB the first time you `make migrate` inside the container, or you can bake the call into a startup script.

---

## Configuration

All settings are validated at startup by [`Settings`](src/app/core/config.py). See [.env.example](.env.example) for the documented list. Highlights:

| Variable                  | Default               | Purpose                                  |
| ------------------------- | --------------------- | ---------------------------------------- |
| `ENVIRONMENT`             | `local`               | Switches docs/reload defaults            |
| `DEBUG`                   | `false`               | FastAPI debug mode                       |
| `LOG_LEVEL` / `LOG_JSON`  | `INFO` / `false`      | Structlog level + JSON renderer toggle   |
| `API_PREFIX`              | `/api`                | Mounts the versioned router prefix       |
| `CORS_ORIGINS`            | (empty)               | Comma-separated list, or `*`             |
| `DB_*`                    | local Postgres defaults | Async DSN, pool sizing, timeouts       |
| `SECRET_KEY`              | _change me_           | For future auth / signing                |
| `REQUEST_ID_HEADER`       | `X-Request-ID`        | Header copied into structured logs       |

### Environment behaviour

- `local` / `development` → `/docs` and `/redoc` enabled, full SQL echo opt-in.
- `production` → docs disabled, JSON logs recommended, generic 500 messages.
- `test` → used by the pytest fixtures; auto-skips DB connectivity check at startup.

---

## Development workflow

```bash
make install        # uv sync --all-extras
make dev            # uvicorn with --reload
make check          # ruff format + ruff lint + mypy
make test           # pytest
make test-cov       # pytest with coverage
```

### Pre-commit hooks (recommended)

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Hooks run the same `ruff`, `ruff format`, and `mypy` that CI runs, so green locally ⇒ green in CI.

---

## Database migrations

Alembic is preconfigured for async PostgreSQL and the `src/` layout.

```bash
make makemigration MSG="add posts table"   # autogenerate from models
make migrate                                # apply migrations
make downgrade                              # roll back one revision
make db-revision                            # show current head
```

Migration scripts are auto-formatted with `ruff` via the `post_write_hooks` in `alembic.ini`. Migration files in `alembic/versions/` are not committed by default — set up your own policy for your team.

---

## Testing

Tests run against an **in-memory SQLite** database via `aiosqlite`, so the suite is fast and hermetic.

```bash
make test
make test-cov
uv run pytest tests/unit -m unit            # unit tests only
uv run pytest tests/integration -m integration
```

The `client` fixture builds the FastAPI app with `dependency_overrides[get_session]` pointing at the test session, and drives it through `httpx.AsyncClient + asgi-lifespan` — no real network, full lifespan events.

---

## Code quality

All tooling is configured in [`pyproject.toml`](pyproject.toml):

- **Ruff** runs a broad rule set (`E`, `W`, `F`, `I`, `B`, `C4`, `UP`, `N`, `ASYNC`, `S`, `SIM`, `RUF`, `PL`, `PT`, `RET`, `PTH`, `TCH`, …) plus formatting.
- **mypy** runs in strict mode with the Pydantic plugin enabled.
- **pytest** is configured with strict markers, strict config, and tracebacks trimmed for readability.

CI fails on any of: format drift, lint findings, type errors, or test failures.

---

## Docker

The included `Dockerfile` is a **multi-stage** build:

1. **builder** — uses the official `uv` image to resolve dependencies into a `.venv` directory.
2. **runtime** — `python:3.13-slim-bookworm`, non-root user, healthcheck against `/api/v1/health`.

The accompanying `docker-compose.yml` brings up the API + a Postgres 17 service with proper `healthcheck` clauses and `depends_on: condition: service_healthy`.

```bash
make docker-build
make docker-up
make docker-logs
make docker-down
```

---

## Production deployment

A non-exhaustive checklist:

- [ ] `ENVIRONMENT=production`
- [ ] `LOG_JSON=true` and ship logs to your aggregator of choice
- [ ] `DEBUG=false`, `DB_ECHO=false`
- [ ] Strong `SECRET_KEY` (32+ random bytes)
- [ ] Explicit `CORS_ORIGINS` allowlist (no `*` in production)
- [ ] Run behind a reverse proxy / TLS terminator (Caddy, nginx, ALB, …)
- [ ] Multiple workers (`API_WORKERS`) and a process supervisor (gunicorn with `uvicorn.workers.UvicornWorker`, or just `uvicorn --workers N`)
- [ ] Health probes wired to `/api/v1/health` (liveness) and `/api/v1/health/ready` (readiness)
- [ ] Database migrations applied as part of the deploy (`alembic upgrade head`)

---

## Architecture

```
┌──────────────────────────────────────────────┐
│            HTTP / FastAPI router             │
│  api/v1/endpoints/*.py  (thin, declarative)  │
└──────────────────────┬───────────────────────┘
                       │ Annotated[Depends(...)]
                       ▼
              ┌──────────────────┐
              │     Services     │  ← business rules, invariants
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │   Repositories   │  ← SQLAlchemy calls live here only
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │  Models (ORM)    │
              └──────────────────┘
```

- **Endpoints** stay thin — parse input, call a service, return a Pydantic model.
- **Services** own the business logic, raise `AppException` subclasses, and never touch SQLAlchemy directly.
- **Repositories** are the only place that builds SQL statements. Subclass `BaseRepository` for richer queries.
- **Models** declare schema; **Schemas** declare the wire format. Never leak ORM types past the service boundary.

Cross-cutting:

- **`core/middleware.py`** attaches an `X-Request-ID` to every request, logs latency, and exposes it on responses.
- **`core/exception_handlers.py`** translates every exception flavour (HTTP, validation, integrity, app-domain) into a consistent JSON envelope.
- **`core/lifespan.py`** verifies DB connectivity at startup and disposes the pool on shutdown.

---

## Adding a new resource

1. **Model** → `src/app/models/<resource>.py` (inherit `Base, TimestampMixin`, export from `models/__init__.py`).
2. **Schema** → `src/app/schemas/<resource>.py` (`Create`, `Update`, `Public` flavours).
3. **Repository** → subclass `BaseRepository[Model]` in `src/app/repositories/<resource>.py`.
4. **Service** → `src/app/services/<resource>.py` (raise `NotFoundError` / `ConflictError` as appropriate).
5. **Dependencies** → add `Annotated[..., Depends(...)]` aliases in `api/deps.py`.
6. **Endpoints** → `src/app/api/v1/endpoints/<resource>.py`; wire into `api/v1/router.py`.
7. **Migration** → `make makemigration MSG="add <resource>"` then `make migrate`.
8. **Tests** → add a `tests/integration/test_<resource>.py`.

---

## API conventions

- **Versioning**: `/api/v1/...`. Breaking changes ship under a new major version.
- **Pagination**: `?page=1&size=20` via `PageParams`; responses use the `Page[T]` envelope with `total`, `pages`, `has_next`, `has_prev`.
- **Identifiers**: UUIDs (preferred for external surfaces) — no exposed sequence IDs.
- **Errors**: RFC 7807-style payloads — `{type, title, status, code, detail, instance, errors?}`.
- **Request IDs**: clients may send `X-Request-ID`; if absent, the server generates one and echoes it back.
- **Partial updates**: `PATCH` with `Update` schemas (all fields optional).

Example error response:

```json
{
  "type": "about:blank#conflict",
  "title": "Conflict",
  "status": 409,
  "code": "conflict",
  "detail": "Username already taken.",
  "instance": "http://localhost:8000/api/v1/users",
  "errors": null
}
```

---

## License

MIT — see [LICENSE](LICENSE).
