"""
pg_advisor — PostgreSQL connector
Priority: CLI arg → ENV var → .env file → error
"""

import os
import sys
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("[ERROR] psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False


# ─────────────────────────────────────────────
# URL resolver — 3 sources, in priority order
# ─────────────────────────────────────────────

def resolve_db_url(cli_url: str | None = None) -> str:
    """
    Returns a valid DB URL from one of three sources:
      1. cli_url  — passed directly from CLI argument
      2. ENV var  — DATABASE_URL in environment
      3. .env     — DATABASE_URL in .env file (project root)

    Raises ValueError if nothing is found.
    """

    # 1. CLI argument
    if cli_url:
        return cli_url.strip()

    # 2. Already in environment
    url = os.environ.get("DATABASE_URL")
    if url:
        return url.strip()

    # 3. .env file (look in cwd and parent dirs up to 3 levels)
    if _DOTENV_AVAILABLE:
        env_path = _find_dotenv()
        if env_path:
            load_dotenv(env_path)
            url = os.environ.get("DATABASE_URL")
            if url:
                return url.strip()

    # Nothing found — give a helpful error
    raise ValueError(
        "\n"
        "  Could not find a DATABASE_URL. Provide it in one of these ways:\n\n"
        "  1. CLI:    pg-advisor analyze postgresql://user:pass@localhost/mydb\n"
        "  2. ENV:    export DATABASE_URL=postgresql://user:pass@localhost/mydb\n"
        "  3. .env:   Add DATABASE_URL=postgresql://... to your .env file\n"
    )


def _find_dotenv() -> Path | None:
    """Walk up from cwd looking for a .env file (max 3 levels)."""
    current = Path.cwd()
    for _ in range(4):
        candidate = current / ".env"
        if candidate.exists():
            return candidate
        current = current.parent
    return None


# ─────────────────────────────────────────────
# Connection
# ─────────────────────────────────────────────

def get_connection(db_url: str):
    """
    Opens a psycopg2 connection.
    Returns (connection, error_message).
    On success: (conn, None)
    On failure: (None, message)
    """
    try:
        conn = psycopg2.connect(db_url)
        conn.set_session(readonly=True, autocommit=True)  # safety: read-only
        return conn, None

    except psycopg2.OperationalError as e:
        msg = str(e).strip()

        # Give friendly hints for common errors
        if "password authentication failed" in msg:
            hint = "Wrong password in your DATABASE_URL."
        elif "could not connect to server" in msg:
            hint = "PostgreSQL server not reachable. Is it running?"
        elif "database" in msg and "does not exist" in msg:
            hint = "Database name in URL does not exist."
        elif "role" in msg and "does not exist" in msg:
            hint = "User/role in URL does not exist on this server."
        else:
            hint = msg

        return None, f"Connection failed: {hint}"

    except Exception as e:
        return None, f"Unexpected error: {e}"


def test_connection(db_url: str) -> bool:
    """Quick check — returns True if connection works."""
    conn, err = get_connection(db_url)
    if conn:
        conn.close()
        return True
    print(f"[ERROR] {err}")
    return False


# ─────────────────────────────────────────────
# Context manager — use in collectors
# ─────────────────────────────────────────────

class PGConnection:
    """
    Use this in collectors:

        with PGConnection(db_url) as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT ...")
            rows = cursor.fetchall()
    """

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = None

    def __enter__(self):
        conn, err = get_connection(self.db_url)
        if not conn:
            raise ConnectionError(err)
        self.conn = conn
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
        return False  # don't suppress exceptions