"""
collectors/db_schema.py

Live PostgreSQL DB se schema data collect karta hai:
  - Tables
  - Columns (name, type, nullable, default)
  - Primary keys
  - Foreign keys
  - Constraints
  - Indexes

Returns: unified dict format jo analyzer samjhe
"""

import psycopg2.extras
from connecter.postgres import PGConnection


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def collect(db_url: str) -> dict:
    """
    DB se poora schema collect karo.
    Returns unified dict.
    """
    with PGConnection(db_url) as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        tables   = _get_tables(cur)
        columns  = _get_columns(cur)
        pks      = _get_primary_keys(cur)
        fks      = _get_foreign_keys(cur)
        indexes  = _get_indexes(cur)
        consts   = _get_constraints(cur)

    return _merge(tables, columns, pks, fks, indexes, consts)


# ─────────────────────────────────────────────
# Individual queries
# ─────────────────────────────────────────────

def _get_tables(cur) -> list[str]:
    """User-defined tables ki list (system tables exclude)."""
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type   = 'BASE TABLE'
        ORDER BY table_name
    """)
    return [row["table_name"] for row in cur.fetchall()]


def _get_columns(cur) -> dict:
    """
    Har table ke columns with:
      - data_type
      - is_nullable
      - column_default
    """
    cur.execute("""
        SELECT
            table_name,
            column_name,
            data_type,
            is_nullable,
            column_default,
            ordinal_position
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """)
    rows = cur.fetchall()

    result = {}
    for row in rows:
        tbl = row["table_name"]
        if tbl not in result:
            result[tbl] = {}
        result[tbl][row["column_name"]] = {
            "type":     row["data_type"],
            "nullable": row["is_nullable"] == "YES",
            "default":  row["column_default"],
            "pk":       False,   # filled below
            "fk":       None,    # filled below
        }
    return result


def _get_primary_keys(cur) -> dict:
    """
    Har table ka primary key column(s).
    Returns: { "users": ["id"], "order_items": ["order_id", "product_id"] }
    """
    cur.execute("""
        SELECT
            tc.table_name,
            kcu.column_name
        FROM information_schema.table_constraints   AS tc
        JOIN information_schema.key_column_usage    AS kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema    = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema    = 'public'
        ORDER BY tc.table_name, kcu.ordinal_position
    """)
    pks = {}
    for row in cur.fetchall():
        tbl = row["table_name"]
        pks.setdefault(tbl, []).append(row["column_name"])
    return pks


def _get_foreign_keys(cur) -> dict:
    """
    Har table ke foreign keys.
    Returns:
    {
      "orders": [
        { "column": "user_id", "ref_table": "users", "ref_column": "id" }
      ]
    }
    """
    cur.execute("""
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name  AS ref_table,
            ccu.column_name AS ref_column,
            tc.constraint_name
        FROM information_schema.table_constraints    AS tc
        JOIN information_schema.key_column_usage     AS kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema    = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema    = 'public'
        ORDER BY tc.table_name
    """)
    fks = {}
    for row in cur.fetchall():
        tbl = row["table_name"]
        fks.setdefault(tbl, []).append({
            "column":     row["column_name"],
            "ref_table":  row["ref_table"],
            "ref_column": row["ref_column"],
        })
    return fks


def _get_indexes(cur) -> dict:
    """
    Har table ke indexes.
    Returns:
    {
      "users": [
        { "name": "idx_users_email", "columns": ["email"], "unique": True }
      ]
    }
    """
    cur.execute("""
        SELECT
            t.relname                         AS table_name,
            i.relname                         AS index_name,
            ix.indisunique                    AS is_unique,
            array_agg(a.attname ORDER BY k)   AS columns
        FROM pg_class      AS t
        JOIN pg_index      AS ix ON t.oid       = ix.indrelid
        JOIN pg_class      AS i  ON i.oid       = ix.indexrelid
        JOIN pg_namespace  AS n  ON t.relnamespace = n.oid
        JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY AS u(attnum, k)
          ON TRUE
        JOIN pg_attribute  AS a
          ON a.attrelid = t.oid AND a.attnum = u.attnum
        WHERE n.nspname = 'public'
          AND t.relkind = 'r'
        GROUP BY t.relname, i.relname, ix.indisunique
        ORDER BY t.relname, i.relname
    """)
    indexes = {}
    for row in cur.fetchall():
        tbl = row["table_name"]
        indexes.setdefault(tbl, []).append({
            "name":    row["index_name"],
            "columns": list(row["columns"]),
            "unique":  row["is_unique"],
        })
    return indexes


def _get_constraints(cur) -> dict:
    """
    Har table ke constraints (UNIQUE, CHECK, NOT NULL).
    Returns: { "users": ["uq_users_email", "chk_age_positive"] }
    """
    cur.execute("""
        SELECT
            table_name,
            constraint_name,
            constraint_type
        FROM information_schema.table_constraints
        WHERE table_schema   = 'public'
          AND constraint_type NOT IN ('PRIMARY KEY', 'FOREIGN KEY')
        ORDER BY table_name, constraint_type
    """)
    consts = {}
    for row in cur.fetchall():
        tbl = row["table_name"]
        consts.setdefault(tbl, []).append({
            "name": row["constraint_name"],
            "type": row["constraint_type"],
        })
    return consts


# ─────────────────────────────────────────────
# Merge everything into unified format
# ─────────────────────────────────────────────

def _merge(tables, columns, pks, fks, indexes, consts) -> dict:
    """
    Sab collectors ka data ek unified dict mein combine karo.
    Yahi dict analyzer ko jayega.
    """
    result = {"tables": {}, "source": "live_db"}

    for tbl in tables:
        tbl_columns = columns.get(tbl, {})

        # Mark PK columns
        for pk_col in pks.get(tbl, []):
            if pk_col in tbl_columns:
                tbl_columns[pk_col]["pk"] = True

        # Mark FK columns
        for fk in fks.get(tbl, []):
            col = fk["column"]
            if col in tbl_columns:
                tbl_columns[col]["fk"] = {
                    "ref_table":  fk["ref_table"],
                    "ref_column": fk["ref_column"],
                }

        result["tables"][tbl] = {
            "columns":     tbl_columns,
            "primary_keys": pks.get(tbl, []),
            "foreign_keys": fks.get(tbl, []),
            "indexes":     indexes.get(tbl, []),
            "constraints": consts.get(tbl, []),
        }

    return result