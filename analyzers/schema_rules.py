"""
analyzers/schema_rules.py

Collected schema data pe rules apply karta hai.
Input:  unified dict (db_schema.py ya model_scanner.py se)
Output: list of Issue objects

Rules covered:
  1. Missing primary key
  2. FLOAT used for money columns
  3. Missing created_at / updated_at
  4. Nullable primary key
  5. FK column without index
  6. Too many columns (God table)
  7. Boolean stored as integer/varchar
  8. Missing NOT NULL on important columns
"""

from dataclasses import dataclass


# ─────────────────────────────────────────────
# Issue dataclass — har rule yahi return karta hai
# ─────────────────────────────────────────────

@dataclass
class Issue:
    severity: str      # "critical" | "warning" | "info"
    table:    str
    column:   str | None
    rule:     str      # rule ID jaise "MISSING_PK"
    message:  str      # human-readable advice
    fix:      str      # suggested fix


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def analyze(schema: dict) -> list[Issue]:
    """
    Schema dict lo, sab rules chalao, issues return karo.

    Usage:
        from pg_advisor.collectors import db_schema
        from pg_advisor.analyzers  import schema_rules

        data   = db_schema.collect(db_url)
        issues = schema_rules.analyze(data)
    """
    issues = []
    tables = schema.get("tables", {})

    for table_name, table_data in tables.items():
        columns     = table_data.get("columns", {})
        primary_keys = table_data.get("primary_keys", [])
        indexes     = table_data.get("indexes", [])
        foreign_keys = table_data.get("foreign_keys", [])

        issues += _check_missing_pk(table_name, primary_keys, columns)
        issues += _check_float_columns(table_name, columns)
        issues += _check_missing_timestamps(table_name, columns)
        issues += _check_nullable_pk(table_name, primary_keys, columns)
        issues += _check_fk_without_index(table_name, foreign_keys, indexes)
        issues += _check_god_table(table_name, columns)
        issues += _check_boolean_as_int(table_name, columns)
        issues += _check_missing_not_null(table_name, columns)

    return issues


# ─────────────────────────────────────────────
# Individual rules
# ─────────────────────────────────────────────

def _check_missing_pk(table, pks, columns) -> list[Issue]:
    """Rule 1: Table mein koi primary key nahi."""
    if not pks:
        return [Issue(
            severity = "critical",
            table    = table,
            column   = None,
            rule     = "MISSING_PK",
            message  = f"Table '{table}' mein koi primary key nahi hai.",
            fix      = f"ALTER TABLE {table} ADD COLUMN id BIGSERIAL PRIMARY KEY;",
        )]
    return []


def _check_float_columns(table, columns) -> list[Issue]:
    """Rule 2: FLOAT ya REAL use ho raha hai — money columns ke liye wrong."""
    issues = []
    # Ye column names money se related lagte hain
    money_hints = {"price", "cost", "amount", "total", "balance",
                   "salary", "fee", "charge", "rate", "tax", "discount"}

    for col_name, col_info in columns.items():
        if col_info.get("type") not in ("float", "real", "double precision"):
            continue

        # Sirf money-sounding columns pe critical, baaki pe warning
        is_money = any(hint in col_name.lower() for hint in money_hints)
        issues.append(Issue(
            severity = "critical" if is_money else "warning",
            table    = table,
            column   = col_name,
            rule     = "FLOAT_FOR_MONEY",
            message  = (
                f"'{table}.{col_name}' FLOAT use kar raha hai — "
                f"floating point precision errors ho sakte hain."
            ),
            fix      = f"ALTER TABLE {table} ALTER COLUMN {col_name} TYPE NUMERIC(12,2);",
        ))
    return issues


def _check_missing_timestamps(table, columns) -> list[Issue]:
    """Rule 3: created_at ya updated_at nahi hai."""
    issues = []
    col_names = set(columns.keys())

    # created_at variants
    has_created = any(c in col_names for c in
                      ("created_at", "created_on", "creation_date",
                       "date_created", "inserted_at"))

    # updated_at variants
    has_updated = any(c in col_names for c in
                      ("updated_at", "modified_at", "last_modified",
                       "date_updated", "modified_on"))

    if not has_created:
        issues.append(Issue(
            severity = "warning",
            table    = table,
            column   = None,
            rule     = "MISSING_CREATED_AT",
            message  = f"Table '{table}' mein created_at nahi — record kab bana pata nahi chalega.",
            fix      = f"ALTER TABLE {table} ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();",
        ))

    if not has_updated:
        issues.append(Issue(
            severity = "info",
            table    = table,
            column   = None,
            rule     = "MISSING_UPDATED_AT",
            message  = f"Table '{table}' mein updated_at nahi — changes track nahi honge.",
            fix      = (
                f"ALTER TABLE {table} ADD COLUMN updated_at TIMESTAMPTZ;\n"
                f"  -- Trigger bhi lagao jo automatically update kare"
            ),
        ))
    return issues


def _check_nullable_pk(table, pks, columns) -> list[Issue]:
    """Rule 4: Primary key column nullable hai — impossible but model se aa sakta hai."""
    issues = []
    for pk_col in pks:
        if pk_col in columns and columns[pk_col].get("nullable"):
            issues.append(Issue(
                severity = "critical",
                table    = table,
                column   = pk_col,
                rule     = "NULLABLE_PK",
                message  = f"'{table}.{pk_col}' primary key hai lekin nullable mark hai — model mein ghalti hai.",
                fix      = f"ALTER TABLE {table} ALTER COLUMN {pk_col} SET NOT NULL;",
            ))
    return issues


def _check_fk_without_index(table, foreign_keys, indexes) -> list[Issue]:
    """Rule 5: FK column pe index nahi — JOINs slow honge."""
    issues = []

    # Indexed columns ki flat list
    indexed_cols = set()
    for idx in indexes:
        for col in idx.get("columns", []):
            indexed_cols.add(col)

    for fk in foreign_keys:
        col = fk.get("column")
        if col and col not in indexed_cols:
            ref = fk.get("ref_table", "?")
            issues.append(Issue(
                severity = "critical",
                table    = table,
                column   = col,
                rule     = "FK_WITHOUT_INDEX",
                message  = (
                    f"'{table}.{col}' → '{ref}' FK hai lekin index nahi — "
                    f"JOIN queries bahut slow honge."
                ),
                fix      = f"CREATE INDEX idx_{table}_{col} ON {table}({col});",
            ))
    return issues


def _check_god_table(table, columns) -> list[Issue]:
    """Rule 6: Bahut zyada columns — God table anti-pattern."""
    count = len(columns)
    if count > 30:
        return [Issue(
            severity = "warning",
            table    = table,
            column   = None,
            rule     = "GOD_TABLE",
            message  = (
                f"Table '{table}' mein {count} columns hain — "
                f"shayad multiple tables mein split karna chahiye."
            ),
            fix      = "Related columns ko alag table mein nikalo — normalization karo.",
        )]
    return []


def _check_boolean_as_int(table, columns) -> list[Issue]:
    """Rule 7: is_active, is_deleted jaise columns integer ya varchar mein hain."""
    issues = []
    bool_hints = {"is_", "has_", "can_", "should_", "allow_", "enable_"}

    for col_name, col_info in columns.items():
        col_type = col_info.get("type", "")
        is_bool_name = any(col_name.lower().startswith(h) for h in bool_hints)

        if is_bool_name and col_type in ("integer", "smallint", "varchar", "char", "text"):
            issues.append(Issue(
                severity = "warning",
                table    = table,
                column   = col_name,
                rule     = "BOOL_AS_INT",
                message  = (
                    f"'{table}.{col_name}' boolean jaisa naam hai lekin "
                    f"type '{col_type}' hai."
                ),
                fix      = f"ALTER TABLE {table} ALTER COLUMN {col_name} TYPE BOOLEAN USING {col_name}::boolean;",
            ))
    return issues


def _check_missing_not_null(table, columns) -> list[Issue]:
    """Rule 8: Important columns nullable hain — email, name, status, etc."""
    issues = []
    important_hints = {"email", "username", "name", "status",
                       "phone", "title", "slug", "type"}

    for col_name, col_info in columns.items():
        if not col_info.get("nullable"):
            continue
        if col_info.get("pk"):
            continue

        is_important = any(hint in col_name.lower() for hint in important_hints)
        if is_important:
            issues.append(Issue(
                severity = "info",
                table    = table,
                column   = col_name,
                rule     = "MISSING_NOT_NULL",
                message  = (
                    f"'{table}.{col_name}' nullable hai — "
                    f"yahan NULL allow karna sahi hai?"
                ),
                fix      = f"ALTER TABLE {table} ALTER COLUMN {col_name} SET NOT NULL;",
            ))
    return issues