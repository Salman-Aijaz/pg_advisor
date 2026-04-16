"""
analyzers/activity_rules.py

pg_stat_activity extension use karta hai — live DB monitoring.

Kya karta hai:
  1. Long-running queries   — threshold se zyada time wali queries
  2. Idle-in-transaction    — transaction open rakhi hui, kuch nahi kar raha
  3. Lock waits             — ek query doosri ka wait kar rahi hai
  4. Connection pool health — max connections ke kitne percent use ho rahe hain

Koi extra extension nahi chahiye — pg_stat_activity PostgreSQL mein
built-in hai (version 9.2+). Sirf pg_stat_activity view read access chahiye.
"""

import psycopg2.extras
from pg_advisor.analyzers.schema_rules import Issue
from pg_advisor.connecter.postgres import PGConnection


# Thresholds — zarurat ho to customize karo
LONG_QUERY_SECONDS      = 30     # 30s se zyada = long running
IDLE_IN_TXN_SECONDS     = 60     # 60s idle-in-transaction = problematic
CONNECTION_WARN_PERCENT = 80     # 80% connections used = warning
CONNECTION_CRIT_PERCENT = 95     # 95% connections used = critical


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def analyze_live(db_url: str) -> list[Issue]:
    """
    Live DB ki current activity scan karo.
    pg_stat_activity se real-time data uthao.
    """
    issues = []

    try:
        with PGConnection(db_url) as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            issues += _check_long_running_queries(cur)
            issues += _check_idle_in_transaction(cur)
            issues += _check_lock_waits(cur)
            issues += _check_connection_pool(cur)

    except Exception as e:
        issues.append(Issue(
            severity = "info",
            table    = "—",
            column   = None,
            rule     = "ACTIVITY_ERROR",
            message  = f"pg_stat_activity check failed: {e}",
            fix      = "verify SELECT permission on the pg_stat_activity view.”",
        ))

    return issues


# ─────────────────────────────────────────────
# Individual checks
# ─────────────────────────────────────────────

def _check_long_running_queries(cur) -> list[Issue]:
    """
    Queries jo LONG_QUERY_SECONDS se zyada se chal rahi hain.
    Active state mein honi chahiye (idle nahi).
    """
    cur.execute("""
        SELECT
            pid,
            usename,
            state,
            ROUND(EXTRACT(EPOCH FROM (now() - query_start))::numeric, 1) AS duration_sec,
            LEFT(query, 150) AS short_query
        FROM pg_stat_activity
        WHERE state     = 'active'
          AND query_start IS NOT NULL
          AND now() - query_start > interval '%s seconds'
          AND query NOT ILIKE '%%pg_stat%%'
          AND query NOT ILIKE '%%pg_advisor%%'
        ORDER BY duration_sec DESC
        LIMIT 5
    """, (LONG_QUERY_SECONDS,))

    rows = cur.fetchall()
    issues = []
    for row in rows:
        issues.append(Issue(
            severity = "critical",
            table    = "—",
            column   = None,
            rule     = "LONG_RUNNING_QUERY",
            message  = (
                f"Query {row['duration_sec']}s it is running successfully."
                f"(user: {row['usename']}, pid: {row['pid']}):\n"
                f"    {row['short_query']}"
            ),
            fix      = (
                f"SELECT pg_cancel_backend({row['pid']});   -- graceful cancel\n"
                f"  -- ya: SELECT pg_terminate_backend({row['pid']});  -- force kill"
            ),
        ))
    return issues


def _check_idle_in_transaction(cur) -> list[Issue]:
    """
    Connections jo 'idle in transaction' hain — transaction open
    rakhi hui lekin kuch nahi kar raha. Locks hold karta hai.
    """
    cur.execute("""
        SELECT
            pid,
            usename,
            ROUND(EXTRACT(EPOCH FROM (now() - state_change))::numeric, 1) AS idle_sec,
            LEFT(query, 150) AS last_query
        FROM pg_stat_activity
        WHERE state = 'idle in transaction'
          AND state_change IS NOT NULL
          AND now() - state_change > interval '%s seconds'
        ORDER BY idle_sec DESC
        LIMIT 5
    """, (IDLE_IN_TXN_SECONDS,))

    rows = cur.fetchall()
    issues = []
    for row in rows:
        issues.append(Issue(
            severity = "critical",
            table    = "—",
            column   = None,
            rule     = "IDLE_IN_TRANSACTION",
            message  = (
                f"Connection {row['idle_sec']}s it is an idle-in-transaction.\n"
                f"(user: {row['usename']}, pid: {row['pid']}) — it is holding locks\n"
                f"    Last query: {row['last_query']}"
            ),
            fix      = (
                f"SELECT pg_terminate_backend({row['pid']});  -- close connection\n"
                f"  -- Set idle_in_transaction_session_timeout on the application side.\n"
                f"  -- ALTER SYSTEM SET idle_in_transaction_session_timeout = '60s';"
            ),
        ))
    return issues


def _check_lock_waits(cur) -> list[Issue]:
    """
    Queries jo kisi lock ka wait kar rahi hain.
    Blocker aur waiter dono dikhao.
    """
    cur.execute("""
        SELECT
            blocked.pid          AS blocked_pid,
            blocked.usename      AS blocked_user,
            blocking.pid         AS blocking_pid,
            blocking.usename     AS blocking_user,
            LEFT(blocked.query, 120)  AS blocked_query,
            LEFT(blocking.query, 120) AS blocking_query,
            ROUND(EXTRACT(EPOCH FROM (now() - blocked.query_start))::numeric, 1) AS wait_sec
        FROM pg_stat_activity AS blocked
        JOIN pg_stat_activity AS blocking
          ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
        WHERE cardinality(pg_blocking_pids(blocked.pid)) > 0
        ORDER BY wait_sec DESC
        LIMIT 5
    """)

    rows = cur.fetchall()
    issues = []
    for row in rows:
        issues.append(Issue(
            severity = "critical",
            table    = "—",
            column   = None,
            rule     = "LOCK_WAIT",
            message  = (
                f"Lock wait detected — pid {row['blocked_pid']} ({row['blocked_user']}) "
                f"{row['wait_sec']}s se wait kar raha hai.\n"
                f"    Blocked query:  {row['blocked_query']}\n"
                f"    Blocking (pid {row['blocking_pid']}): {row['blocking_query']}"
            ),
            fix      = (
                f"SELECT pg_cancel_backend({row['blocking_pid']});  -- cancel blocker\n"
                f"  -- Root cause: long transactions, missing indexes, or application logic"
            ),
        ))
    return issues


def _check_connection_pool(cur) -> list[Issue]:
    """
    Total connections vs max_connections.
    80%+ = warning, 95%+ = critical.
    """
    cur.execute("""
        SELECT
            COUNT(*)                                         AS total_connections,
            (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_connections,
            COUNT(*) FILTER (WHERE state = 'active')        AS active,
            COUNT(*) FILTER (WHERE state = 'idle')          AS idle,
            COUNT(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_txn
        FROM pg_stat_activity
        WHERE pid <> pg_backend_pid()
    """)

    row = cur.fetchone()
    if not row:
        return []

    total   = row["total_connections"]
    maximum = row["max_connections"]
    if not maximum or maximum == 0:
        return []

    pct = (total / maximum) * 100

    if pct < CONNECTION_WARN_PERCENT:
        return []

    severity = "critical" if pct >= CONNECTION_CRIT_PERCENT else "warning"

    return [Issue(
        severity = severity,
        table    = "—",
        column   = None,
        rule     = "CONNECTION_POOL_PRESSURE",
        message  = (
            f"Connection pool {pct:.1f}% full "
            f"({total}/{maximum} connections). "
            f"Active: {row['active']}, Idle: {row['idle']}, "
            f"Idle-in-txn: {row['idle_in_txn']}."
        ),
        fix      = (
            "-- Use PgBouncer or a connection pooler\n"
            "-- or increase max_connections (postgresql.conf):\n"
            "ALTER SYSTEM SET max_connections = 200;\n"
            "SELECT pg_reload_conf();"
        ),
    )]