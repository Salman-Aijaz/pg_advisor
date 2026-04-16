"""
cli.py — pg-advisor main entry point
"""

import sys
import argparse

from pg_advisor.connecter.postgres import resolve_db_url
from pg_advisor.collectors import db_schema, model_scanner
from pg_advisor.analyzers  import schema_rules, index_rules, query_rules
from pg_advisor.analyzers  import hypopg_rules, activity_rules
from pg_advisor.reporters  import cli_reporter, md_reporter


class _HelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_help_position", 32)
        kwargs.setdefault("width", 90)
        super().__init__(*args, **kwargs)


MAIN_DESCRIPTION = """\
pg-advisor — PostgreSQL Schema & Query Advisor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Connects to your PostgreSQL database, scans your schema and queries,
and reports actionable issues with ready-to-run SQL fixes.

  Detects: missing indexes, wrong data types, slow queries,
           duplicate indexes, missing constraints, lock waits,
           idle-in-transaction connections, and more.

Examples:
  pg-advisor setup                                  # check extensions first
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
  pg-advisor analyze --skip-activity              # skip live monitoring
"""

SETUP_DESCRIPTION = """\
Check which PostgreSQL extensions are available and which need to be installed.

Run this before your first analyze to confirm everything is set up correctly.

Examples:
  pg-advisor setup postgresql://user:pass@localhost:5432/mydb
  pg-advisor setup   # reads DATABASE_URL from env
"""


def main():
    parser = argparse.ArgumentParser(
        prog            = "pg-advisor",
        description     = MAIN_DESCRIPTION,
        formatter_class = _HelpFormatter,
    )
    parser.add_argument("--version", action="version", version="pg-advisor 0.2.0")

    sub = parser.add_subparsers(
        dest    = "command",
        title   = "Available commands",
        metavar = "<command>",
    )

    # ── setup subcommand ──────────────────────
    setup_cmd = sub.add_parser(
        "setup",
        help            = "Check required PostgreSQL extensions",
        description     = SETUP_DESCRIPTION,
        formatter_class = _HelpFormatter,
    )
    setup_cmd.add_argument(
        "db_url", nargs="?", default=None, metavar="DATABASE_URL",
        help=(
            "PostgreSQL connection URL.\n"
            "Omit to read from DATABASE_URL env variable or .env file."
        ),
    )

    # ── analyze subcommand ────────────────────
    analyze_cmd = sub.add_parser(
        "analyze",
        help            = "Scan a database and report issues",
        description     = ANALYZE_DESCRIPTION,
        formatter_class = _HelpFormatter,
    )
    analyze_cmd.add_argument(
        "db_url", nargs="?", default=None, metavar="DATABASE_URL",
        help=(
            "PostgreSQL connection URL.\n"
            "Format : postgresql://user:password@host:port/dbname\n"
            "Example: postgresql://postgres:secret@localhost:5432/myapp\n"
            "Tip    : Omit to read from DATABASE_URL env variable or .env file."
        ),
    )
    analyze_cmd.add_argument(
        "--models-path", metavar="PATH", default=None,
        help=(
            "Path to model file or folder — scan without live DB.\n"
            "Supports: SQLAlchemy (models.py), Django ORM, plain .sql files.\n"
            "Example : --models-path ./app/models/"
        ),
    )
    analyze_cmd.add_argument(
        "--skip-queries", action="store_true",
        help=(
            "Skip slow-query and SELECT * analysis.\n"
            "Use if pg_stat_statements is not installed."
        ),
    )
    analyze_cmd.add_argument(
        "--skip-hypopg", action="store_true",
        help=(
            "Skip hypothetical index testing via hypopg.\n"
            "Use if hypopg extension is not installed."
        ),
    )
    analyze_cmd.add_argument(
        "--skip-activity", action="store_true",
        help=(
            "Skip live connection monitoring (pg_stat_activity).\n"
            "Skips: long queries, idle-in-transaction, lock waits, connection pool."
        ),
    )
    analyze_cmd.add_argument(
        "--save-report", action="store_true",
        help=(
            "Automatically save a Markdown (.md) report — no prompt.\n"
            "Saved to: ./pgadvisor_report/pg_advisor_report_YYYYMMDD_HHMMSS.md"
        ),
    )
    analyze_cmd.add_argument(
        "--no-report", action="store_true",
        help="Do not save a Markdown report. Useful in CI/CD pipelines.",
    )

    args = parser.parse_args()

    if args.command == "setup":
        run_setup(args)
    elif args.command == "analyze":
        run_analyze(args)
    else:
        parser.print_help()


# ─────────────────────────────────────────────
# setup command
# ─────────────────────────────────────────────

def run_setup(args):
    """
    DB se connect karo aur check karo kaunsi extensions available hain.
    Developer ko clearly batao kya install karna hai.
    """
    try:
        db_url = resolve_db_url(args.db_url)
    except ValueError as e:
        print(str(e))
        sys.exit(1)

    import psycopg2
    import psycopg2.extras

    print()
    print("pg-advisor — Extension Setup Check")
    print("━" * 44)

    try:
        conn = psycopg2.connect(db_url)
        conn.set_session(readonly=True, autocommit=True)
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception as e:
        print(f"\n  ❌ Could not connect: {e}\n")
        sys.exit(1)

    extensions = [
        {
            "name":     "pg_stat_activity",
            "type":     "built-in",
            "purpose":  "Live query monitoring, lock waits, connection pool",
            "install":  None,
        },
        {
            "name":     "pg_stat_statements",
            "type":     "built-in (disabled by default)",
            "purpose":  "Slow query detection, SELECT * usage, high-frequency queries",
            "install":  (
                "1. Add to postgresql.conf:\n"
                "      shared_preload_libraries = 'pg_stat_statements'\n"
                "   2. Restart PostgreSQL\n"
                "   3. Run in your DB:\n"
                "      CREATE EXTENSION pg_stat_statements;"
            ),
        },
        {
            "name":     "hypopg",
            "type":     "third-party",
            "purpose":  "Hypothetical index testing — confirms index will actually help",
            "install":  (
                "Ubuntu/Debian:\n"
                "      sudo apt install postgresql-<version>-hypopg\n"
                "   macOS (Homebrew):\n"
                "      brew install hypopg\n"
                "   Then in your DB:\n"
                "      CREATE EXTENSION hypopg;"
            ),
        },
    ]

    all_ok   = True
    missing  = []

    for ext in extensions:
        name = ext["name"]

        # pg_stat_activity is always available — just check connection
        if name == "pg_stat_activity":
            try:
                cur.execute("SELECT 1 FROM pg_stat_activity LIMIT 1")
                available = True
            except Exception:
                available = False
        else:
            try:
                cur.execute(
                    "SELECT 1 FROM pg_extension WHERE extname = %s", (name,)
                )
                available = cur.fetchone() is not None
            except Exception:
                available = False

        icon  = "✅" if available else "⚠ "
        label = "available" if available else "not found"

        print(f"\n  {icon} {name}")
        print(f"     Type   : {ext['type']}")
        print(f"     Purpose: {ext['purpose']}")
        print(f"     Status : {label}")

        if not available:
            all_ok = False
            missing.append(ext)

    conn.close()

    print()
    print("━" * 44)

    if all_ok:
        print("  ✅ All extensions available — ready to run analyze!\n")
        return

    print(f"  ⚠  {len(missing)} extension(s) not found — some checks will be skipped.\n")
    for ext in missing:
        if ext["install"]:
            print(f"  To enable {ext['name']}:")
            for line in ext["install"].split("\n"):
                print(f"     {line}")
            print()

    print("  pg-advisor analyze will still work — missing extensions are skipped gracefully.")
    print("  Run 'pg-advisor setup' again after installing to confirm.\n")


# ─────────────────────────────────────────────
# analyze command
# ─────────────────────────────────────────────

def run_analyze(args):
    all_issues = []

    try:
        db_url = resolve_db_url(args.db_url)
    except ValueError as e:
        print(str(e))
        sys.exit(1)

    source_label = db_url.split("@")[-1]
    _log("Connecting to database...")

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

    if not args.skip_queries:
        _log("Analyzing query statistics (pg_stat_statements)...")
        all_issues += query_rules.analyze_live(db_url)
    else:
        _log("Query analysis skipped (--skip-queries).")

    if not args.skip_hypopg:
        _log("Testing hypothetical indexes (hypopg)...")
        all_issues += hypopg_rules.analyze_live(db_url, db_data)
    else:
        _log("Hypothetical index testing skipped (--skip-hypopg).")

    if not args.skip_activity:
        _log("Checking live connection activity (pg_stat_activity)...")
        all_issues += activity_rules.analyze_live(db_url)
    else:
        _log("Activity monitoring skipped (--skip-activity).")

    if args.models_path:
        _log(f"Scanning model files at: {args.models_path}")
        model_data = model_scanner.collect(args.models_path)
        scanned    = model_data.get("files_scanned", [])
        _log(f"Scanned {len(scanned)} file(s).")
        all_issues += schema_rules.analyze(model_data)
        all_issues += index_rules.analyze(model_data)

    cli_reporter.report(all_issues, source_label=source_label)
    _handle_report_prompt(all_issues, source_label, args)


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


def _log(msg: str) -> None:
    print(f"[pg-advisor] {msg}")

def _err(msg: str) -> None:
    print(f"[pg-advisor] ERROR: {msg}", file=sys.stderr)


if __name__ == "__main__":
    main()