"""
cli.py — pg-advisor main entry point
"""

import sys
import argparse

from pg_advisor.connecter.postgres import resolve_db_url
from pg_advisor.collectors          import db_schema, model_scanner
from pg_advisor.analyzers           import schema_rules, index_rules, query_rules
from pg_advisor.reporters           import cli_reporter, md_reporter


# ─────────────────────────────────────────────
# Custom formatter — wider help, aligned columns
# ─────────────────────────────────────────────

class _HelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_help_position", 32)
        kwargs.setdefault("width", 90)
        super().__init__(*args, **kwargs)


# ─────────────────────────────────────────────
# CLI definition
# ─────────────────────────────────────────────

MAIN_DESCRIPTION = """\
pg-advisor — PostgreSQL Schema & Query Advisor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Connects to your PostgreSQL database, scans your schema and queries,
and reports actionable issues with ready-to-run SQL fixes.

  Detects: missing indexes, wrong data types, slow queries,
           duplicate indexes, missing constraints, and more.

Examples:
  pg-advisor analyze postgresql://user:pass@localhost/mydb
  pg-advisor analyze --models-path ./models/
  pg-advisor analyze --save-report --skip-queries
"""

ANALYZE_DESCRIPTION = """\
Analyze a PostgreSQL database and report schema, index, and query issues.

Provide the database URL as an argument, or set the DATABASE_URL
environment variable, or add it to a .env file in your project root.

Examples:
  pg-advisor analyze postgresql://user:pass@localhost:5432/mydb
  pg-advisor analyze                              # reads DATABASE_URL from env
  pg-advisor analyze --models-path ./models/      # also scan model files
  pg-advisor analyze --save-report                # auto-save Markdown report
  pg-advisor analyze --skip-queries --no-report   # schema only, no report
"""


def main():
    parser = argparse.ArgumentParser(
        prog             = "pg-advisor",
        description      = MAIN_DESCRIPTION,
        formatter_class  = _HelpFormatter,
        add_help         = True,
    )
    parser.add_argument(
        "--version", action="version", version="pg-advisor 0.1.0",
    )

    sub = parser.add_subparsers(
        dest        = "command",
        title       = "Available commands",
        metavar     = "<command>",
    )

    # ── analyze subcommand ────────────────────
    analyze_cmd = sub.add_parser(
        "analyze",
        help            = "Scan a database and report issues",
        description     = ANALYZE_DESCRIPTION,
        formatter_class = _HelpFormatter,
        add_help        = True,
    )

    analyze_cmd.add_argument(
        "db_url",
        nargs   = "?",
        default = None,
        metavar = "DATABASE_URL",
        help    = (
            "PostgreSQL connection URL.\n"
            "Format : postgresql://user:password@host:port/dbname\n"
            "Example: postgresql://postgres:secret@localhost:5432/myapp\n"
            "Tip    : Omit this to read from the DATABASE_URL env variable\n"
            "         or a .env file in your current directory."
        ),
    )

    analyze_cmd.add_argument(
        "--models-path",
        metavar = "PATH",
        default = None,
        help    = (
            "Path to a model file or folder to scan for schema issues\n"
            "without a live DB connection.\n"
            "Supports: SQLAlchemy (models.py), Django ORM, plain .sql files.\n"
            "Example : --models-path ./app/models/\n"
            "Example : --models-path .  (scans entire project)"
        ),
    )

    analyze_cmd.add_argument(
        "--skip-queries",
        action  = "store_true",
        help    = (
            "Skip slow-query and SELECT * analysis.\n"
            "Use this if pg_stat_statements is not installed,\n"
            "or to speed up the scan on large databases."
        ),
    )

    analyze_cmd.add_argument(
        "--save-report",
        action  = "store_true",
        help    = (
            "Automatically save a Markdown (.md) report after the scan\n"
            "without prompting. The file is saved to:\n"
            "  ./pgadvisor_report/pg_advisor_report_YYYYMMDD_HHMMSS.md"
        ),
    )

    analyze_cmd.add_argument(
        "--no-report",
        action  = "store_true",
        help    = (
            "Do not save a Markdown report and skip the prompt.\n"
            "Useful in CI/CD pipelines or automated scripts."
        ),
    )

    args = parser.parse_args()

    if args.command == "analyze":
        run_analyze(args)
    else:
        parser.print_help()


# ─────────────────────────────────────────────
# Core analyze flow
# ─────────────────────────────────────────────

def run_analyze(args):
    all_issues = []

    # Step 1: Resolve DB URL
    try:
        db_url = resolve_db_url(args.db_url)
    except ValueError as e:
        print(str(e))
        sys.exit(1)

    source_label = db_url.split("@")[-1]

    _log("Connecting to database...")

    # Step 2: Live DB schema
    try:
        _log("Collecting schema...")
        db_data = db_schema.collect(db_url)
        tables  = list(db_data["tables"].keys())
        _log(f"Found {len(tables)} table(s): {', '.join(tables)}")

        all_issues += schema_rules.analyze(db_data)
        all_issues += index_rules.analyze(db_data)
        all_issues += index_rules.analyze_live(db_url)

    except ConnectionError as e:
        _err(f"Could not connect to database: {e}")
        sys.exit(1)

    # Step 3: Query stats
    if not args.skip_queries:
        _log("Analyzing query statistics...")
        all_issues += query_rules.analyze_live(db_url)
    else:
        _log("Query analysis skipped (--skip-queries).")

    # Step 4: Model file scan
    if args.models_path:
        _log(f"Scanning model files at: {args.models_path}")
        model_data = model_scanner.collect(args.models_path)
        scanned    = model_data.get("files_scanned", [])
        _log(f"Scanned {len(scanned)} file(s).")
        all_issues += schema_rules.analyze(model_data)
        all_issues += index_rules.analyze(model_data)

    # Step 5: Terminal report
    cli_reporter.report(all_issues, source_label=source_label)

    # Step 6: Markdown report
    _handle_report_prompt(all_issues, source_label, args)


# ─────────────────────────────────────────────
# Report prompt
# ─────────────────────────────────────────────

def _handle_report_prompt(issues, source_label, args):
    if args.no_report:
        return
    if args.save_report:
        _save_md_report(issues, source_label)
        return

    print()
    print("─" * 50)
    try:
        answer = input("  Save Markdown (.md) report? (yes/no): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  Non-interactive mode — report skipped.")
        return

    if answer in ("yes", "y"):
        _save_md_report(issues, source_label)
    else:
        print("  Report not saved.\n")


def _save_md_report(issues, source_label):
    print()
    try:
        content  = md_reporter.generate(issues, source_label=source_label)
        filepath = md_reporter.save(content)
        print(f"  ✅ Report saved at: {filepath}\n")
    except RuntimeError as e:
        _err(f"Could not save report:\n  {e}")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _log(msg: str) -> None:
    print(f"[pg-advisor] {msg}")

def _err(msg: str) -> None:
    print(f"[pg-advisor] ERROR: {msg}", file=sys.stderr)


if __name__ == "__main__":
    main()