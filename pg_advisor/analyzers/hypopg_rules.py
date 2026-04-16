"""
analyzers/hypopg_rules.py

hypopg extension use karta hai — hypothetical indexes test karta hai.

Kya karta hai:
  - FK columns pe hypothetical index banata hai
  - EXPLAIN pe run karta hai aur cost compare karta hai
  - Agar cost improve hoti hai → confirmed suggestion deta hai
  - Agar nahi hoti → silently skip

hypopg extension required:
  CREATE EXTENSION hypopg;

Without hypopg: ye analyzer gracefully skip ho jata hai,
koi crash nahi, sirf ek INFO issue return karta hai.
"""

import psycopg2.extras
from pg_advisor.analyzers.schema_rules import Issue
from pg_advisor.connecter.postgres    import PGConnection


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def analyze_live(db_url: str, schema: dict) -> list[Issue]:
    """
    Live DB pe hypothetical index testing karo.

    Flow:
      1. hypopg available hai? — check karo
      2. FK columns dhundo jinka index nahi
      3. Har ek pe hypopg se fake index banao
      4. EXPLAIN ANALYZE run karo — cost check karo
      5. Cost improve hua? → confirmed issue add karo
      6. hypopg_reset() se sab fake indexes saaf karo
    """
    issues = []

    try:
        with PGConnection(db_url) as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Step 1: Extension check
            if not _hypopg_available(cur):
                issues.append(Issue(
                    severity = "info",
                    table    = "—",
                    column   = None,
                    rule     = "HYPOPG_NOT_INSTALLED",
                    message  = "HypoPG extension is not installed skipping hypothetical index testing.",
                    fix      = "CREATE EXTENSION hypopg;  -- then re-run pg-advisor",
                ))
                return issues

            # Step 2: FK candidates collect karo schema se
            candidates = _collect_fk_candidates(schema)
            if not candidates:
                return issues

            # Step 3 + 4 + 5: Har candidate test karo
            for table, column in candidates:
                result = _test_hypothetical_index(cur, table, column)
                if result:
                    issues.append(result)

            # Step 6: Cleanup — sab fake indexes drop karo
            try:
                cur.execute("SELECT hypopg_reset();")
            except Exception:
                pass

    except Exception as e:
        issues.append(Issue(
            severity = "info",
            table    = "—",
            column   = None,
            rule     = "HYPOPG_ERROR",
            message  = f"hypopg analysis fail hua: {e}",
            fix      = "Check hypopg extension and permissions.",
        ))

    return issues


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _hypopg_available(cur) -> bool:
    """hypopg extension install hai?"""
    try:
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'hypopg'")
        return cur.fetchone() is not None
    except Exception:
        return False


def _collect_fk_candidates(schema: dict) -> list[tuple[str, str]]:
    """
    Schema se un FK columns ki list banao
    jinke paas index nahi hai.
    ye wahi candidates hain jo hypopg test karega.
    """
    candidates = []
    for table_name, table_data in schema.get("tables", {}).items():
        foreign_keys = table_data.get("foreign_keys", [])
        indexes      = table_data.get("indexes", [])

        indexed_cols = {
            col
            for idx in indexes
            for col in idx.get("columns", [])
        }

        for fk in foreign_keys:
            col = fk.get("column")
            if col and col not in indexed_cols:
                candidates.append((table_name, col))

    return candidates


def _test_hypothetical_index(cur, table: str, column: str) -> Issue | None:
    """
    Ek hypothetical index banao, EXPLAIN cost compare karo.
    Improvement mili → Issue return karo.
    Nahi mili → None return karo.
    """
    try:
        # Cost WITHOUT index
        cur.execute(f"EXPLAIN (FORMAT JSON) SELECT * FROM {table} WHERE {column} = 1")
        before = cur.fetchone()
        cost_before = _extract_cost(before)

        # Hypothetical index banao
        cur.execute(
            "SELECT * FROM hypopg_create_index(%s)",
            (f"CREATE INDEX ON {table}({column})",)
        )
        idx_row   = cur.fetchone()
        hypo_name = idx_row.get("index_name", "")

        # Cost WITH hypothetical index
        cur.execute(f"EXPLAIN (FORMAT JSON) SELECT * FROM {table} WHERE {column} = 1")
        after = cur.fetchone()
        cost_after = _extract_cost(after)

        # Drop this specific hypothetical index
        if hypo_name:
            try:
                cur.execute("SELECT hypopg_drop_index(%s)", (idx_row.get("indexrelid"),))
            except Exception:
                pass

        # No improvement — skip
        if cost_before is None or cost_after is None:
            return None
        if cost_after >= cost_before * 0.9:  # 10% threshold
            return None

        improvement = round((1 - cost_after / cost_before) * 100, 1)

        return Issue(
            severity = "critical",
            table    = table,
            column   = column,
            rule     = "HYPOPG_INDEX_CONFIRMED",
            message  = (
                f"'{table}.{column}' “By adding the index, the query cost will decrease "
                f"{improvement}% — verified by HypoPG."
            ),
            fix      = f"CREATE INDEX idx_{table}_{column} ON {table}({column});",
        )

    except Exception:
        return None


def _extract_cost(explain_row) -> float | None:
    """EXPLAIN JSON output se total cost nikalo."""
    try:
        import json
        if explain_row is None:
            return None
        raw = list(explain_row.values())[0]
        if isinstance(raw, str):
            raw = json.loads(raw)
        return float(raw[0]["Plan"]["Total Cost"])
    except Exception:
        return None