"""
analyzers/index_rules.py

Index-related issues dhundta hai.

Rules:
  1. Duplicate indexes — same columns pe multiple indexes
  2. Unused indexes — pg_stat_user_indexes se
  3. Index on low-cardinality column (boolean, status)
"""

import psycopg2.extras
from pg_advisor.analyzers.schema_rules import Issue
from pg_advisor.connecter.postgres import PGConnection


# ─────────────────────────────────────────────
# Model-based rules (bina DB ke)
# ─────────────────────────────────────────────

def analyze(schema: dict) -> list[Issue]:
    """Schema dict se index issues nikalo."""
    issues = []
    tables = schema.get("tables", {})

    for table_name, table_data in tables.items():
        indexes = table_data.get("indexes", [])
        columns = table_data.get("columns", {})

        issues += _check_duplicate_indexes(table_name, indexes)
        issues += _check_low_cardinality_index(table_name, indexes, columns)

    return issues


def _check_duplicate_indexes(table, indexes) -> list[Issue]:
    issues  = []
    seen    = {}

    for idx in indexes:
        key = tuple(sorted(idx.get("columns", [])))
        if key in seen:
            issues.append(Issue(
                severity = "warning",
                table    = table,
                column   = None,
                rule     = "DUPLICATE_INDEX",
                message  = (
                    f"Duplicate index found on '{table}' for columns {list(key)}: "
                    f"'{idx['name']}' and '{seen[key]}'."
                ),
                fix      = f"DROP INDEX {idx['name']};  -- or drop '{seen[key]}'",
            ))
        else:
            seen[key] = idx["name"]
    return issues

def _check_low_cardinality_index(table, indexes, columns) -> list[Issue]:
    issues = []
    low_cardinality_types = {"boolean", "bool"}
    low_cardinality_names = {"status", "is_active", "is_deleted",
                              "gender", "type", "flag"}

    for idx in indexes:
        if len(idx.get("columns", [])) != 1:
            continue

        col = idx["columns"][0]
        col_info = columns.get(col, {})
        col_type = col_info.get("type", "")

        is_low_type = col_type in low_cardinality_types
        is_low_name = col.lower() in low_cardinality_names

        if is_low_type or is_low_name:
            issues.append(Issue(
                severity = "info",
                table    = table,
                column   = col,
                rule     = "LOW_CARDINALITY_INDEX",
                message  = (
                    f"Index exists on '{table}.{col}', but this appears to be a "
                    f"low-cardinality column — index benefit will be limited."
                ),
                fix      = (
                    f"DROP INDEX {idx['name']};  "
                    f"-- Consider partial index: CREATE INDEX ON {table}({col}) WHERE {col} = true;"
                ),
            ))
    return issues

# ─────────────────────────────────────────────
# Live DB rules (pg_stat se)
# ─────────────────────────────────────────────

def analyze_live(db_url: str) -> list[Issue]:
    """
    Live DB se unused indexes dhundo.
    Ye sirf tab call karo jab real DB available ho.
    """
    issues = []
    try:
        with PGConnection(db_url) as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            issues += _check_unused_indexes(cur)
    except Exception as e:
        print(f"  [index_rules] Live check skip: {e}")
    return issues




def _check_unused_indexes(cur) -> list[Issue]:
    """pg_stat_user_indexes se indexes jo kabhi use nahi hue."""
    cur.execute("""
        SELECT
            schemaname,
            relname      AS table_name,
            indexrelname AS index_name,
            idx_scan     AS times_used
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
          AND idx_scan   = 0
          AND indexrelname NOT LIKE '%_pkey'
        ORDER BY relname, indexrelname
    """)
    rows = cur.fetchall()
    issues = []
    for row in rows:
        issues.append(Issue(
            severity = "warning",
            table    = row["table_name"],
            column   = None,
            rule     = "UNUSED_INDEX",
            message  = (
                f"Index '{row['index_name']}' on '{row['table_name']}' "
                f"has never been used (idx_scan = 0)."
            ),
            fix      = f"DROP INDEX {row['index_name']};  -- verify before dropping",
        ))
    return issues