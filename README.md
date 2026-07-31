# FastAPI Boilerplate

A starting point for a real FastAPI service: async SQLAlchemy 2.0, Pydantic v2, a layered
architecture, structured logging, RFC 7807 errors, migrations, and a test suite that runs
with no infrastructure at all.

Works with **PostgreSQL, MySQL, SQLite, or MongoDB** — one command picks whichever your
machine can actually reach.

```bash
./scripts/setup.sh && make dev
```

**Two ways to read this:**

- **[Start here](#part-1--getting-started)** if you are new to FastAPI. It explains what every
  file does and where your code goes.
- **[Skip to the reference →](#part-2--reference)** if you have shipped FastAPI before and just
  want the conventions, the layout, and the knobs.

---

## Requirements

| | |
| --- | --- |
| **Python** | **3.13 or newer.** 3.13 and 3.14 are tested in CI on every push. Older versions are not supported and will not work — the code uses PEP 695 type parameters (`class Repo[T]`) and `StrEnum`, which 3.12 cannot parse. |
| **Operating system** | Linux, macOS, or Windows via WSL2. The setup script also runs under Git Bash. |
| **A database** | Optional. With no database server installed, the project uses SQLite — a plain file, nothing to run. |
| **Everything else** | Installed for you by `./scripts/setup.sh`, including Python itself. |

---

# Part 1 — Getting started

*Already comfortable with FastAPI? [Jump to Part 2](#part-2--reference).*

## 1. Set it up

```bash
git clone <your-repo-url>
cd fastapi-boilerplate
./scripts/setup.sh
```

That one script:

1. Installs [uv](https://docs.astral.sh/uv/) (the tool that manages Python and packages) if you don't have it.
2. Installs Python 3.13.
3. Creates your `.env` file and generates a real `SECRET_KEY`.
4. Looks for a database. Finds PostgreSQL, MySQL, or MongoDB running? It uses it. Finds nothing — or finds a server it cannot log in to? It falls back to **SQLite**, so you are never blocked.
5. Installs dependencies and creates the database tables.

It is safe to run again any time. It never overwrites an existing `.env`.

```bash
./scripts/setup.sh --db sqlite   # skip detection, just use SQLite
./scripts/setup.sh --yes         # never ask questions
./scripts/setup.sh --help        # every option
```

## 2. Run it

```bash
make dev
```

Open <http://localhost:8000/docs>. That page is generated from your code — every endpoint,
every field, every error shape. You can send real requests from it.

Try the endpoints that ship with the project:

```bash
curl http://localhost:8000/api/v1/health

curl -X POST http://localhost:8000/api/v1/users \
  -H 'Content-Type: application/json' \
  -d '{"username": "alice", "email": "alice@example.com"}'

curl http://localhost:8000/api/v1/users
```

## 3. Understand the layout

A request flows **down** through four layers and the answer comes back up. Each layer has one
job, and only talks to the one below it.

```
      HTTP request
           │
           ▼
   api/v1/endpoints/     "parse the request, return the response"
           │              ── no business rules, no SQL
           ▼
      services/          "the rules": is this allowed? is the name taken?
           │              ── no SQL, no HTTP
           ▼
    repositories/        "talk to the database" — the only place queries live
           │
           ▼
   models/ (SQL tables)
```

Why bother? Because business rules that live inside an HTTP handler can only be used by that
handler. Move them one layer down and a CLI command, a background job, or a test can use them too.

### Where things live

| I want to… | Edit this |
| --- | --- |
| Add or change an endpoint (URL, status code) | [src/app/api/v1/endpoints/](src/app/api/v1/endpoints/) |
| Change the shape of JSON coming in or going out | [src/app/schemas/](src/app/schemas/) |
| Add a rule ("only admins", "name must be unique") | [src/app/services/](src/app/services/) |
| Write or change a database query | [src/app/repositories/](src/app/repositories/) |
| Add a column or a table | [src/app/models/](src/app/models/) — then `make makemigration MSG="..."` |
| Add a setting or environment variable | [src/app/core/config.py](src/app/core/config.py) and [.env.example](.env.example) |
| Add a new error type | [src/app/core/exceptions.py](src/app/core/exceptions.py) |
| Register a new URL prefix | [src/app/api/v1/router.py](src/app/api/v1/router.py) |
| Change what happens at startup/shutdown | [src/app/core/lifespan.py](src/app/core/lifespan.py) |

### Every file, briefly

```
src/app/
├── main.py                 Builds the app: middleware, error handlers, routers
├── __main__.py             `python -m app` — runs the server using .env
│
├── api/
│   ├── deps.py             Shared dependencies; picks the database adapter
│   ├── router.py           Mounts /api
│   └── v1/
│       ├── router.py       Mounts /api/v1/<thing> — register new routers here
│       └── endpoints/      One file per resource: health.py, users.py
│
├── core/                   Cross-cutting concerns, no business logic
│   ├── config.py           Every setting, validated at startup
│   ├── logging.py          structlog setup; JSON logs in production
│   ├── exceptions.py       NotFoundError, ConflictError, … raise these
│   ├── exception_handlers.py  Turns exceptions into consistent JSON
│   ├── middleware.py       Request IDs and access logs
│   └── lifespan.py         Startup checks and shutdown cleanup
│
├── db/
│   ├── base.py             The SQLAlchemy Base all models inherit
│   ├── mixins.py           TimestampMixin: created_at / updated_at
│   ├── types.py            UtcDateTime: timestamps behave the same everywhere
│   ├── session.py          Engine and per-request session (SQL backends)
│   └── mongo.py            Client and database handle (MongoDB backend)
│
├── domain/                 Plain records passed between layers.
│                           They exist so the service layer works unchanged
│                           whether the data came from SQL or MongoDB.
├── models/                 SQLAlchemy tables (SQL backends only)
├── schemas/                Pydantic models = the JSON contract
├── repositories/
│   ├── protocols.py        What a repository must provide
│   ├── sql/                PostgreSQL / MySQL / SQLite implementation
│   └── mongo/              MongoDB implementation
└── services/               Business logic
```

## 4. Add your first resource

Say you want `/api/v1/posts`. Copy the five `user` files and adjust — in this order:

**1. The table** — `src/app/models/post.py`

```python
class Post(Base, TimestampMixin):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
```

Export it from `models/__init__.py`, or Alembic will not see it.

**2. The JSON shapes** — `src/app/schemas/post.py`: `PostCreate` (what you accept),
`PostUpdate` (all fields optional), `PostPublic` (what you return). Keep them separate — you
rarely want to accept everything you return.

**3. The queries** — `src/app/repositories/sql/post.py`, subclassing `BaseSqlRepository[Post]`.

**4. The rules** — `src/app/services/post.py`. Raise `NotFoundError` / `ConflictError`; they
become 404 / 409 automatically.

**5. The endpoints** — `src/app/api/v1/endpoints/posts.py`, then register the router:

```python
# src/app/api/v1/router.py
router.include_router(posts.router, prefix="/posts", tags=["posts"])
```

**6. The migration** — you changed the database, so record it:

```bash
make makemigration MSG="add posts"   # writes alembic/versions/xxxx_add_posts.py — read it
make migrate                          # applies it
```

**7. A test** — `tests/integration/test_posts.py`. The `client` fixture gives you a working
app with a throwaway database:

```python
async def test_create_post(client):
    response = await client.post("/api/v1/posts", json={"title": "Hello"})
    assert response.status_code == 201
```

## 5. The commands you'll use

```bash
make dev      # run with auto-reload
make test     # run the tests
make check    # format, lint, type-check, test — run before you commit
make help     # everything else
```

## 6. When something breaks

| Symptom | Cause and fix |
| --- | --- |
| `password authentication failed` at startup | `.env` credentials don't match your database. Fix them, or run `./scripts/setup.sh --db sqlite` to sidestep it. |
| `relation "users" does not exist` | Migrations haven't run: `make migrate`. |
| `ModuleNotFoundError: No module named 'app'` | Run through `uv` (`make dev`, `uv run …`), not a bare `python`. |
| Changed a model but nothing changed in the DB | Models don't alter tables. `make makemigration MSG="…"` then `make migrate`. |
| `make dev` fails on a fresh clone | Re-run `./scripts/setup.sh` — it is safe to repeat. |
| Anything else | `make doctor` prints your versions and the configured backend. |

---

# Part 2 — Reference

## Stack

| Concern | Choice |
| --- | --- |
| Language | Python 3.13+ (3.13 and 3.14 in CI) |
| Framework | FastAPI ≥ 0.141, Starlette 1.x |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| Databases | PostgreSQL (asyncpg), MySQL (aiomysql), SQLite (aiosqlite), MongoDB (pymongo async) |
| Validation | Pydantic v2 + pydantic-settings |
| Logging | structlog |
| Packaging | uv, PEP 735 dependency groups |
| Quality | Ruff, mypy `--strict`, pytest |

## Choosing a backend

Set `DB_BACKEND` in `.env`, or set `DATABASE_URL` and every `DB_*` value is ignored:

```bash
DB_BACKEND=sqlite                                        # no server needed
DB_BACKEND=postgres                                      # default
DB_BACKEND=mysql        # uv sync --extra mysql
DB_BACKEND=mongodb      # uv sync --extra mongodb

DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db  # takes priority
DATABASE_URL=postgres://user:pass@host:5432/db            # driver added for you
```

PostgreSQL and SQLite drivers ship by default. MySQL and MongoDB are extras, so nobody
installs a driver they will not use.

**What differs per backend:**

- `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` are ignored by SQLite (a file has no connection pool).
- `DB_STATEMENT_TIMEOUT_MS` is a real statement timeout on PostgreSQL; on MongoDB it is the
  server-selection timeout; MySQL and SQLite ignore it.
- SQLite connections get `foreign_keys=ON`, WAL journaling, and a busy timeout — none of which
  are SQLite defaults, all of which you want in a web app.
- MongoDB has no migrations. Uniqueness lives in `repositories/mongo/user.py:INDEXES` and is
  applied at startup. Alembic refuses to run against it, loudly.

## Architecture

```
api/v1/endpoints  →  services  →  repositories  →  models / documents
      thin            rules         all queries        storage
```

- **Endpoints** parse input and return a Pydantic model. No rules, no SQL.
- **Services** hold the rules and raise `AppException` subclasses. No SQL, no HTTP types.
- **Repositories** are the only place a query is built. They satisfy
  `repositories/protocols.py`, which is why one service works against SQL and MongoDB alike.
- **Domain records** (`domain/`) are what crosses the service boundary — never an ORM object,
  never a raw document.

`tests/integration/test_repository_contract.py` runs one set of assertions against every
adapter, so a backend that drifts from the contract fails CI.

Cross-cutting:

- `core/middleware.py` — attaches `X-Request-ID` (honouring an inbound one), logs method,
  path, status and duration, and exposes both headers to browsers via CORS.
- `core/exception_handlers.py` — maps every exception flavour to one JSON envelope.
- `core/lifespan.py` — checks the database at startup, creates MongoDB indexes, disposes pools
  on shutdown.

## Configuration

Everything is validated by `Settings` at import time; a bad value stops the process instead of
producing a confusing 500 later. See [.env.example](.env.example) for the annotated list.

Production configs are checked, not just parsed. With `ENVIRONMENT=production` the app refuses
to start if `SECRET_KEY` is still the default, `DEBUG` is on, or CORS allows `*` with
credentials.

Environment behaviour:

| `ENVIRONMENT` | Effect |
| --- | --- |
| `local`, `development`, `staging` | `/docs`, `/redoc`, `/api/openapi.json` served |
| `production` | Docs disabled; unsafe configuration rejected at startup |
| `test` | Startup database check skipped (the fixtures own the database) |

## Migrations

```bash
make makemigration MSG="add posts"   # autogenerate, then read the file
make migrate                          # upgrade head
make downgrade                        # back one revision
make db-revision                      # what the database is on
make db-reset                         # wipe and re-apply (destructive)
```

Autogenerate writes SQL for the backend you generated against. If you target more than one,
check the diff for frozen dialect-specific defaults — prefer `sa.func.now()` over
`sa.text("now()")`. `alembic/versions/0001_create_users_table.py` is written this way and runs
on all three SQL backends.

Batch mode turns on automatically for SQLite, which cannot `ALTER` most things in place.

## Testing

```bash
make test                                    # everything
make test-cov                                # with coverage
uv run pytest tests/unit -m unit             # fast, no I/O
uv run pytest -m "not mongodb"               # skip backend-specific tests
```

Each test gets a fresh in-memory SQLite database, so the suite is hermetic and needs nothing
installed. The MongoDB parameters of the contract test skip themselves when no server is
reachable; CI runs them against a real MongoDB service.

## Code quality

- **Ruff** for lint and format; **mypy `--strict`** over `src` and `tests`.
- `make check` runs exactly what CI runs.
- Optional: `uv run pre-commit install` to run the same checks on commit.

## Running in production

```bash
uv sync --frozen --no-dev     # runtime dependencies only
uv run alembic upgrade head   # migrate as part of the deploy
uv run python -m app          # honours API_HOST / API_PORT / API_WORKERS
```

Checklist:

- [ ] `ENVIRONMENT=production`, `DEBUG=false`, `LOG_JSON=true`
- [ ] `SECRET_KEY` from `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- [ ] `CORS_ORIGINS` listing explicit origins
- [ ] `API_WORKERS` set — and remember `DB_POOL_SIZE + DB_MAX_OVERFLOW` connections **per
      worker**, which must stay under your server's `max_connections`
- [ ] Behind a TLS terminator; `python -m app` already trusts forwarded headers in production
- [ ] `/api/v1/health` as the liveness probe, `/api/v1/health/ready` as readiness (it returns
      503, not 500, when the database is unreachable)

## API conventions

- **Versioning** — `/api/v1/…`; breaking changes go under a new version.
- **Pagination** — `?page=1&size=20`; responses carry `total`, `pages`, `has_next`, `has_prev`.
  Ordering includes the id as a tiebreaker so pages never repeat a row.
- **Identifiers** — UUIDs, never sequence ids.
- **Errors** — RFC 7807-shaped: `{type, title, status, code, detail, instance, errors?}`.
- **Timestamps** — always UTC and timezone-aware, on every backend.
- **Request ids** — send `X-Request-ID` or one is generated; it comes back on the response and
  appears in every log line for that request.

```json
{
  "type": "about:blank#conflict",
  "title": "Conflict",
  "status": 409,
  "code": "conflict",
  "detail": "Username already taken.",
  "instance": "http://localhost:8000/api/v1/users",
  "errors": { "field": "username" }
}
```

## License

MIT — see [LICENSE](LICENSE).
