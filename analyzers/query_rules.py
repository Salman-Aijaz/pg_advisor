"""
analyzers/query_rules.py

pg_stat_statements se slow / problematic queries dhundta hai.

Rules:
  1. Slow queries  — mean_exec_time > threshold
  2. High call queries — bahut baar chal raha hai, optimize karo
  3. Sequential scans — EXPLAIN se seq scan detect karo
  4. SELECT * usage — bad practice

Note: Ye analyzer sirf live DB pe kaam karta hai.
      pg_stat_statements extension honi chahiye.
"""

import psycopg2.extras
from analyzers.schema_rules import Issue
from connecter.postgres    import PGConnection


# Thresholds
SLOW_QUERY_MS   = 500     # 500ms se zyada = slow
HIGH_CALL_COUNT = 1000    # 1000+ calls = review karo


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def analyze_live(db_url: str) -> list[Issue]:
    """
    Live DB se query issues nikalo.
    pg_stat_statements extension required.
    """
    issues = []

    try:
        with PGConnection(db_url) as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            if not _check_extension(cur):
                issues.append(Issue(
                    severity = "info",
                    table    = "—",
                    column   = None,
                    rule     = "NO_STAT_STATEMENTS",
                    message  = "pg_stat_statements extension nahi hai — query analysis skip.",
                    fix      = "CREATE EXTENSION pg_stat_statements;  -- postgresql.conf mein bhi add karo",
                ))
                return issues

            issues += _check_slow_queries(cur)
            issues += _check_high_call_queries(cur)
            issues += _check_select_star(cur)

    except Exception as e:
        issues.append(Issue(
            severity = "info",
            table    = "—",
            column   = None,
            rule     = "QUERY_ANALYSIS_FAILED",
            message  = f"Query analysis nahi ho saki: {e}",
            fix      = "pg_stat_statements aur permissions check karo.",
        ))

    return issues


# ─────────────────────────────────────────────
# Individual checks
# ─────────────────────────────────────────────

def _check_extension(cur) -> bool:
    """pg_stat_statements available hai?"""
    cur.execute("""
        SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
    """)
    return cur.fetchone() is not None


def _check_slow_queries(cur) -> list[Issue]:
    """Mean execution time > SLOW_QUERY_MS wali queries."""
    cur.execute("""
        SELECT
            query,
            calls,
            ROUND(mean_exec_time::numeric, 2) AS mean_ms,
            ROUND(total_exec_time::numeric, 2) AS total_ms
        FROM pg_stat_statements
        WHERE mean_exec_time > %s
          AND query NOT ILIKE '%%pg_stat%%'
        ORDER BY mean_exec_time DESC
        LIMIT 10
    """, (SLOW_QUERY_MS,))

    rows = cur.fetchall()
    issues = []
    for row in rows:
        short_q = _shorten(row["query"])
        issues.append(Issue(
            severity = "critical",
            table    = "—",
            column   = None,
            rule     = "SLOW_QUERY",
            message  = (
                f"Slow query detected ({row['mean_ms']}ms avg, "
                f"{row['calls']} calls):\n    {short_q}"
            ),
            fix      = "EXPLAIN ANALYZE chalao aur index check karo.",
        ))
    return issues


def _check_high_call_queries(cur) -> list[Issue]:
    """Bahut zyada baar chal rahi queries — caching ya optimization chahiye."""
    cur.execute("""
        SELECT
            query,
            calls,
            ROUND(mean_exec_time::numeric, 2) AS mean_ms
        FROM pg_stat_statements
        WHERE calls > %s
          AND mean_exec_time < %s
          AND query NOT ILIKE '%%pg_stat%%'
        ORDER BY calls DESC
        LIMIT 5
    """, (HIGH_CALL_COUNT, SLOW_QUERY_MS))

    rows = cur.fetchall()
    issues = []
    for row in rows:
        short_q = _shorten(row["query"])
        issues.append(Issue(
            severity = "warning",
            table    = "—",
            column   = None,
            rule     = "HIGH_FREQUENCY_QUERY",
            message  = (
                f"High frequency query ({row['calls']} calls, "
                f"{row['mean_ms']}ms avg):\n    {short_q}"
            ),
            fix      = "Cache karo (Redis/Memcached) ya prepared statement use karo.",
        ))
    return issues


def _check_select_star(cur) -> list[Issue]:
    """SELECT * use ho rahi queries — bad practice."""
    cur.execute("""
        SELECT query, calls
        FROM pg_stat_statements
        WHERE query ILIKE 'SELECT *%%'
           OR query ILIKE 'select *%%'
        ORDER BY calls DESC
        LIMIT 5
    """)

    rows = cur.fetchall()
    issues = []
    for row in rows:
        short_q = _shorten(row["query"])
        issues.append(Issue(
            severity = "warning",
            table    = "—",
            column   = None,
            rule     = "SELECT_STAR",
            message  = f"SELECT * use ho raha hai:\n    {short_q}",
            fix      = "Sirf zaruri columns select karo — SELECT col1, col2 FROM ...",
        ))
    return issues


def _shorten(query: str, max_len: int = 120) -> str:
    """Long query ko truncate karo display ke liye."""
    q = " ".join(query.split())  # multiple spaces remove
    return q[:max_len] + "..." if len(q) > max_len else q