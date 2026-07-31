#!/usr/bin/env bash
#
# Set this project up on whatever machine you happen to be on.
#
# It installs uv and Python if needed, creates .env with a real secret key,
# finds a database you can actually reach, installs dependencies, and applies
# migrations. Nothing is assumed to be present and nothing is pinned to one
# vendor — if there is no database server anywhere, it falls back to SQLite,
# which needs no server at all.
#
# Safe to re-run: every step checks before it acts.
#
#   ./scripts/setup.sh                  # detect everything, ask when unsure
#   ./scripts/setup.sh --db sqlite      # skip detection, use SQLite
#   ./scripts/setup.sh --yes            # never prompt (CI, containers)
#   ./scripts/setup.sh --help           # all options
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# --- defaults, all overridable from the environment --------------------------
PYTHON_VERSION="${PYTHON_VERSION:-$(cat .python-version 2>/dev/null || echo 3.13)}"
DB_CHOICE="${DB_CHOICE:-auto}"      # auto | postgres | mysql | sqlite | mongodb
ASSUME_YES="${ASSUME_YES:-0}"
RUN_INSTALL=1
RUN_MIGRATE=1

# --- pretty output, degrading to plain text when not a terminal --------------
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; GREEN=$'\033[32m'
    YELLOW=$'\033[33m'; BLUE=$'\033[36m'; RESET=$'\033[0m'
else
    BOLD=""; DIM=""; RED=""; GREEN=""; YELLOW=""; BLUE=""; RESET=""
fi

step()  { printf '\n%s==>%s %s%s%s\n' "$BLUE" "$RESET" "$BOLD" "$1" "$RESET"; }
ok()    { printf '  %s✓%s %s\n' "$GREEN" "$RESET" "$1"; }
info()  { printf '  %s·%s %s\n' "$DIM" "$RESET" "$1"; }
warn()  { printf '  %s!%s %s\n' "$YELLOW" "$RESET" "$1"; }
die()   { printf '\n  %s✗ %s%s\n\n' "$RED" "$1" "$RESET" >&2; exit 1; }

has() { command -v "$1" >/dev/null 2>&1; }

confirm() {
    # confirm "question" -> 0 for yes. Non-interactive runs take the default.
    [ "$ASSUME_YES" = "1" ] && return 0
    [ -t 0 ] || return 0
    local reply
    printf '  %s?%s %s [Y/n] ' "$YELLOW" "$RESET" "$1"
    read -r reply
    [[ -z "$reply" || "$reply" =~ ^[Yy] ]]
}

usage() {
    cat <<'EOF'
Usage: ./scripts/setup.sh [options]

Options:
  --db BACKEND     auto (default), postgres, mysql, sqlite, or mongodb.
                   "auto" probes for a running server and falls back to sqlite.
  --python X.Y     Python version to use (default: from .python-version).
  --yes, -y        Never prompt; accept every default. Use in CI.
  --no-install     Skip dependency installation.
  --no-migrate     Skip database migrations.
  --help, -h       Show this message.

Environment:
  DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME override what is probed
  and written to .env. DATABASE_URL, if already set in .env, is left alone.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --db)         DB_CHOICE="${2:-}"; shift 2 ;;
        --db=*)       DB_CHOICE="${1#*=}"; shift ;;
        --python)     PYTHON_VERSION="${2:-}"; shift 2 ;;
        --python=*)   PYTHON_VERSION="${1#*=}"; shift ;;
        -y|--yes)     ASSUME_YES=1; shift ;;
        --no-install) RUN_INSTALL=0; shift ;;
        --no-migrate) RUN_MIGRATE=0; shift ;;
        -h|--help)    usage; exit 0 ;;
        *)            die "Unknown option: $1 (try --help)" ;;
    esac
done

case "$DB_CHOICE" in
    auto|postgres|mysql|sqlite|mongodb) ;;
    *) die "--db must be auto, postgres, mysql, sqlite, or mongodb (got '$DB_CHOICE')" ;;
esac

# =============================================================================
# 1. Toolchain
# =============================================================================
step "Checking your system"

case "$(uname -s)" in
    Linux*)   OS="Linux" ;;
    Darwin*)  OS="macOS" ;;
    MINGW*|MSYS*|CYGWIN*)
        OS="Windows"
        warn "Git Bash detected. WSL2 is the smoother path on Windows." ;;
    *) OS="$(uname -s)" ;;
esac
info "$OS on $(uname -m)"

if ! has uv; then
    info "uv is not installed (it manages Python and dependencies for this project)"
    if confirm "Install uv now?"; then
        if has curl;   then curl -LsSf https://astral.sh/uv/install.sh | sh
        elif has wget; then wget -qO- https://astral.sh/uv/install.sh | sh
        else die "Need curl or wget to install uv. See https://docs.astral.sh/uv/"
        fi
        # The installer drops uv here; pick it up without a new shell.
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
        has uv || die "uv installed but is not on PATH. Open a new terminal and re-run."
    else
        die "uv is required. Install it from https://docs.astral.sh/uv/ and re-run."
    fi
fi
ok "uv $(uv --version | awk '{print $2}')"

uv python install "$PYTHON_VERSION" >/dev/null 2>&1 || true
ok "Python $PYTHON_VERSION ready"

# =============================================================================
# 2. Find a database
# =============================================================================
step "Choosing a database"

DB_HOST="${DB_HOST:-localhost}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_NAME="${DB_NAME:-fastapi_db}"

port_open() {
    # port_open HOST PORT — true if something is listening.
    local host="$1" port="$2"
    if has nc; then nc -z -w2 "$host" "$port" >/dev/null 2>&1
    elif has timeout; then timeout 2 bash -c ">/dev/tcp/$host/$port" >/dev/null 2>&1
    else bash -c ">/dev/tcp/$host/$port" >/dev/null 2>&1  # macOS has no `timeout`
    fi
}

detect_backend() {
    if has pg_isready && pg_isready -h "$DB_HOST" -q >/dev/null 2>&1; then
        echo postgres; return
    fi
    port_open "$DB_HOST" "${DB_PORT:-5432}" && { echo postgres; return; }
    port_open "$DB_HOST" 3306 && { echo mysql; return; }
    port_open "$DB_HOST" 27017 && { echo mongodb; return; }
    echo sqlite
}

if [ "$DB_CHOICE" = "auto" ]; then
    # Braces are required: bash 3.2 (macOS) folds a following multibyte
    # character into the variable name.
    info "Looking for a database server on ${DB_HOST}..."
    DB_BACKEND="$(detect_backend)"
    if [ "$DB_BACKEND" = "sqlite" ]; then
        info "No database server found — using SQLite (a file, no server needed)"
        info "Point at a real server later by editing DB_BACKEND in .env"
    else
        ok "Found $DB_BACKEND"
    fi
else
    DB_BACKEND="$DB_CHOICE"
    info "Using $DB_BACKEND (you asked for it explicitly)"
fi

# Only these backends need a driver that is not installed by default.
EXTRA_ARGS=()
case "$DB_BACKEND" in
    mysql)   EXTRA_ARGS=(--extra mysql) ;;
    mongodb) EXTRA_ARGS=(--extra mongodb) ;;
esac

case "$DB_BACKEND" in
    postgres) DB_PORT="${DB_PORT:-5432}" ;;
    mysql)    DB_PORT="${DB_PORT:-3306}"; DB_USER="${DB_USER/postgres/root}" ;;
    mongodb)  DB_PORT="${DB_PORT:-27017}" ;;
    sqlite)   DB_PORT="" ;;
esac

# =============================================================================
# 3. .env
# =============================================================================
step "Writing .env"

generate_secret() {
    if has openssl; then openssl rand -base64 48 | tr -d '\n/+=' | cut -c1-64
    elif has python3; then python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
    elif has shasum; then date +%s | shasum -a 256 | cut -c1-64
    else echo "change-me-$(date +%s)"
    fi
}

set_env_var() {
    # set_env_var KEY VALUE — add or replace a key in .env, preserving comments.
    local key="$1" value="$2"
    if grep -qE "^${key}=" .env 2>/dev/null; then
        # A literal replacement, so passwords with / & | survive intact.
        python3 - "$key" "$value" <<'PY'
import pathlib, sys
key, value = sys.argv[1], sys.argv[2]
path = pathlib.Path(".env")
lines = path.read_text().splitlines()
for index, line in enumerate(lines):
    if line.startswith(f"{key}="):
        lines[index] = f"{key}={value}"
        break
path.write_text("\n".join(lines) + "\n")
PY
    else
        printf '%s=%s\n' "$key" "$value" >> .env
    fi
}

if [ -f .env ]; then
    ok ".env already exists — leaving your settings alone"
    if grep -qE '^DATABASE_URL=.+' .env; then
        info "DATABASE_URL is set; it overrides every DB_* value"
    fi
else
    cp .env.example .env
    set_env_var SECRET_KEY "$(generate_secret)"
    set_env_var DB_BACKEND "$DB_BACKEND"
    set_env_var DB_HOST "$DB_HOST"
    set_env_var DB_PORT "$DB_PORT"
    set_env_var DB_USER "$DB_USER"
    set_env_var DB_PASSWORD "$DB_PASSWORD"
    set_env_var DB_NAME "$DB_NAME"
    ok "Created .env (backend: $DB_BACKEND, with a freshly generated SECRET_KEY)"
fi

# =============================================================================
# 4. Dependencies
# =============================================================================
if [ "$RUN_INSTALL" = "1" ]; then
    step "Installing dependencies"
    uv sync ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
    if [ ${#EXTRA_ARGS[@]} -gt 0 ]; then
        ok "Installed into .venv, with the $DB_BACKEND driver"
    else
        ok "Installed into .venv"
    fi
else
    info "Skipping dependency installation (--no-install)"
fi

# =============================================================================
# 5. Database preparation
# =============================================================================
verify_connection() {
    # Prints the reason on failure; silent on success.
    uv run ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} python - <<'PY' 2>&1
import asyncio, sys
from app import db

try:
    asyncio.run(db.ping())
except Exception as exc:
    sys.stdout.write(f"{type(exc).__name__}: {exc}".split("\n")[0][:160])
    sys.exit(1)
PY
}

if [ "$RUN_MIGRATE" = "1" ]; then
    step "Preparing the database"

    case "$DB_BACKEND" in
        postgres)
            if has psql; then
                if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
                        -lqt >/dev/null 2>&1; then
                    if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
                            -lqt | cut -d'|' -f1 | grep -qw "$DB_NAME"; then
                        PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" \
                            -U "$DB_USER" "$DB_NAME" 2>/dev/null \
                            && ok "Created database '$DB_NAME'" \
                            || warn "Could not create '$DB_NAME' — create it yourself, then re-run"
                    else
                        ok "Database '$DB_NAME' exists"
                    fi
                else
                    warn "Could not authenticate as '$DB_USER'. Fix DB_USER/DB_PASSWORD in .env."
                fi
            else
                info "psql not installed — assuming '$DB_NAME' already exists"
            fi
            ;;
        mysql)
            if has mysql; then
                mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" \
                    ${DB_PASSWORD:+-p"$DB_PASSWORD"} \
                    -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\`;" 2>/dev/null \
                    && ok "Database '$DB_NAME' ready" \
                    || warn "Could not create '$DB_NAME' — create it yourself, then re-run"
            else
                info "mysql client not installed — assuming '$DB_NAME' already exists"
            fi
            ;;
        sqlite)
            ok "SQLite needs no setup — the file is created on first use"
            ;;
        mongodb)
            ok "MongoDB creates collections on demand; indexes are built at startup"
            ;;
    esac

    # Ask the application itself whether it can reach the database. Using the
    # app's own code means this checks exactly what startup will check.
    if [ "$RUN_INSTALL" = "1" ] && ! connection_error="$(verify_connection)"; then
        warn "Cannot connect: $connection_error"
        if [ "$DB_CHOICE" = "auto" ]; then
            info "Falling back to SQLite so you have something that works right now"
            set_env_var DB_BACKEND sqlite
            DB_BACKEND=sqlite
            EXTRA_ARGS=()
            ok "Switched .env to SQLite — set DB_BACKEND back once $DB_HOST accepts your credentials"
        else
            warn "You asked for $DB_BACKEND explicitly, so nothing was changed."
            warn "Fix DB_USER / DB_PASSWORD / DB_NAME in .env, then run: make migrate"
        fi
    fi

    if [ "$DB_BACKEND" = "mongodb" ]; then
        info "Skipping migrations — MongoDB has no schema to migrate"
    elif uv run ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} alembic upgrade head >/dev/null 2>&1; then
        ok "Migrations applied — the 'users' table exists"
    else
        warn "Migrations failed. Check .env, then run: make migrate"
    fi
else
    info "Skipping migrations (--no-migrate)"
fi

# =============================================================================
# Done
# =============================================================================
printf '\n%s✓ Setup complete.%s\n\n' "$GREEN$BOLD" "$RESET"
printf '  Start the server:   %smake dev%s\n' "$BOLD" "$RESET"
printf '  Then open:          %shttp://localhost:8000/docs%s\n' "$BOLD" "$RESET"
printf '  Run the tests:      %smake test%s\n\n' "$BOLD" "$RESET"
