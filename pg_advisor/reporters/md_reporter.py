"""
reporters/md_reporter.py

Issues ko proper Markdown file mein save karta hai.

Features:
  - Headings, tables, SQL code blocks — proper MD syntax
  - Dynamic filename: pg_advisor_report_YYYYMMDD_HHMMSS.md
  - Saves inside ./pgadvisor_report/ folder (cross-platform)
  - Error handling — no silent failures
  - Modular: md_reporter.generate() → string, save() → path
"""

import os
from datetime import datetime
from pathlib  import Path

from pg_advisor.analyzers.schema_rules import Issue


SEVERITY_ICONS = {
    "critical": "❌",
    "warning":  "⚠️",
    "info":     "ℹ️",
}

OUTPUT_DIR = "pgadvisor_report"


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def generate(issues: list[Issue], source_label: str = "Analysis") -> str:
    """
    Issues list lo → Markdown string return karo.
    Saving se alag rakha taake test ya reuse ho sake.
    """
    lines = []

    _header(lines, source_label, issues)
    _summary_table(lines, issues)
    _per_table_sections(lines, issues)
    _rule_reference(lines)

    return "\n".join(lines)


def save(content: str) -> Path:
    """
    Markdown content ko file mein save karo.

    - Folder: ./pgadvisor_report/
    - Filename: pg_advisor_report_YYYYMMDD_HHMMSS.md
    - Returns: absolute Path of saved file
    - Raises: RuntimeError on any failure (no silent errors)
    """
    # ── Directory banana ──────────────────────
    output_dir = Path.cwd() / OUTPUT_DIR
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(
            f"Report folder banana fail hua: '{output_dir}'\n  Reason: {e}\n"
            f"  Check karo: kya current directory mein write permission hai?"
        ) from e

    # ── Filename ──────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"pg_advisor_report_{timestamp}.md"
    filepath  = output_dir / filename

    # ── Overwrite guard ───────────────────────
    if filepath.exists():
        raise RuntimeError(
            f"File already exists (same second mein run hua?): {filepath}"
        )

    # ── Write ─────────────────────────────────
    try:
        filepath.write_text(content, encoding="utf-8")
    except OSError as e:
        raise RuntimeError(
            f"File likhna fail hua: '{filepath}'\n  Reason: {e}"
        ) from e

    return filepath.resolve()


# ─────────────────────────────────────────────
# Markdown builders (internal)
# ─────────────────────────────────────────────

def _header(lines: list, source_label: str, issues: list[Issue]) -> None:
    criticals = sum(1 for i in issues if i.severity == "critical")
    warnings  = sum(1 for i in issues if i.severity == "warning")
    infos     = sum(1 for i in issues if i.severity == "info")
    total     = len(issues)
    ts        = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines += [
        "# pg-advisor Report",
        "",
        f"**Database:** `{source_label}`  ",
        f"**Generated:** {ts}  ",
        f"**Total Issues:** {total}",
        "",
        "| Severity | Count |",
        "|----------|-------|",
        f"| ❌ Critical | {criticals} |",
        f"| ⚠️ Warning  | {warnings}  |",
        f"| ℹ️ Info     | {infos}     |",
        "",
        "---",
        "",
    ]


def _summary_table(lines: list, issues: list[Issue]) -> None:
    if not issues:
        lines += ["## ✅ No Issues Found", "", "Database clean lag raha hai!", ""]
        return

    lines += [
        "## Issue Summary",
        "",
        "| Table | Column | Severity | Rule | Message |",
        "|-------|--------|----------|------|---------|",
    ]

    for issue in sorted(issues, key=lambda i: (_severity_order(i.severity), i.table)):
        icon   = SEVERITY_ICONS.get(issue.severity, "•")
        col    = f"`{issue.column}`" if issue.column else "—"
        table  = f"`{issue.table}`"
        msg    = issue.message.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {table} | {col} | {icon} {issue.severity} | `{issue.rule}` | {msg} |")

    lines += ["", "---", ""]


def _per_table_sections(lines: list, issues: list[Issue]) -> None:
    lines += ["## Detailed Findings", ""]

    # Group by table
    by_table: dict[str, list[Issue]] = {}
    for issue in issues:
        by_table.setdefault(issue.table, []).append(issue)

    for table_name in sorted(by_table.keys()):
        table_issues = sorted(by_table[table_name], key=lambda i: _severity_order(i.severity))

        lines += [f"### Table: `{table_name}`", ""]

        for issue in table_issues:
            icon = SEVERITY_ICONS.get(issue.severity, "•")
            col  = f"`.{issue.column}`" if issue.column else ""

            lines += [
                f"#### {icon} `{issue.rule}`{col}",
                "",
                f"**Severity:** {issue.severity.upper()}  ",
                f"**Message:** {issue.message}",
                "",
                "**Recommended Fix:**",
                "```sql",
            ]

            # Multi-line fix support
            for fix_line in issue.fix.strip().split("\n"):
                lines.append(fix_line.strip())

            lines += ["```", ""]

        lines += ["---", ""]


def _rule_reference(lines: list) -> None:
    lines += [
        "## Rule Reference",
        "",
        "| Rule ID | Category | What it checks |",
        "|---------|----------|----------------|",
        "| `MISSING_PK` | Schema | Table bina primary key ke |",
        "| `FLOAT_FOR_MONEY` | Schema | FLOAT column for price/balance/total |",
        "| `FK_WITHOUT_INDEX` | Schema | Foreign key column pe index nahi |",
        "| `NULLABLE_PK` | Schema | Primary key nullable mark hai |",
        "| `MISSING_CREATED_AT` | Schema | created_at column nahi hai |",
        "| `MISSING_UPDATED_AT` | Schema | updated_at column nahi hai |",
        "| `BOOL_AS_INT` | Schema | is_*/has_* column wrong type mein |",
        "| `GOD_TABLE` | Schema | 30+ columns — normalize karo |",
        "| `MISSING_NOT_NULL` | Schema | Important column nullable hai |",
        "| `DUPLICATE_INDEX` | Index | Same columns pe 2+ indexes |",
        "| `UNUSED_INDEX` | Index | Index kabhi use nahi hua |",
        "| `LOW_CARDINALITY_INDEX` | Index | Boolean/status pe index |",
        "| `SLOW_QUERY` | Query | 500ms+ avg execution time |",
        "| `HIGH_FREQUENCY_QUERY` | Query | 1000+ calls — cache karo |",
        "| `SELECT_STAR` | Query | SELECT * bad practice |",
        "",
        "---",
        "",
        "*Generated by [pg-advisor](https://github.com/Salman-Aijaz/pg-advisor)*",
    ]


# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────

def _severity_order(s: str) -> int:
    return {"critical": 0, "warning": 1, "info": 2}.get(s, 9)