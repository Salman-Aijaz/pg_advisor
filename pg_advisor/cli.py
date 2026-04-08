"""
cli.py — pg-advisor ka main entry point

Usage:
  pg-advisor analyze postgresql://user:pass@localhost/mydb
  pg-advisor analyze --models-path ./models/
  pg-advisor analyze  (DATABASE_URL env se uthayega)
"""

import sys
import argparse

from pg_advisor.connecter.postgres   import resolve_db_url
from pg_advisor.collectors            import db_schema, model_scanner
from pg_advisor.analyzers             import schema_rules, index_rules, query_rules
from pg_advisor.reporters             import cli_reporter, md_reporter


def main():
    parser = argparse.ArgumentParser(
        prog        = "pg-advisor",
        description = "PostgreSQL schema & query advisor",
    )
    sub = parser.add_subparsers(dest="command")

    analyze_cmd = sub.add_parser("analyze", help="DB analyze")
    analyze_cmd.add_argument(
        "db_url", nargs="?", default=None,
        help="postgresql://user:pass@host/db  (ya DATABASE_URL env set karo)",
    )
    analyze_cmd.add_argument(
        "--models-path", default=None,
        help="models.py / schema.py ya folder path (optional)",
    )
    analyze_cmd.add_argument(
        "--skip-queries", action="store_true",
        help="pg_stat_statements check skip karo",
    )
    analyze_cmd.add_argument(
        "--save-report", action="store_true",
        help="Seedha report save karo — prompt skip",
    )
    analyze_cmd.add_argument(
        "--no-report", action="store_true",
        help="Report save mat karo — prompt skip",
    )

    args = parser.parse_args()

    if args.command == "analyze":
        run_analyze(args)
    else:
        parser.print_help()


def run_analyze(args):
    all_issues = []

    # Step 1: DB URL resolve
    try:
        db_url = resolve_db_url(args.db_url)
    except ValueError as e:
        print(str(e))
        sys.exit(1)

    source_label = db_url.split("@")[-1]

    _log("Connecting to DB...")

    # Step 2: Live DB schema
    try:
        _log("Collecting schema from DB...")
        db_data = db_schema.collect(db_url)
        tables  = list(db_data["tables"].keys())
        _log(f"{len(tables)} tables found: {', '.join(tables)}")

        all_issues += schema_rules.analyze(db_data)
        all_issues += index_rules.analyze(db_data)
        all_issues += index_rules.analyze_live(db_url)

    except ConnectionError as e:
        _err(f"DB connect nahi hua: {e}")
        sys.exit(1)

    # Step 3: Query stats
    if not args.skip_queries:
        _log("Checking query stats...")
        all_issues += query_rules.analyze_live(db_url)

    # Step 4: Model files
    if args.models_path:
        _log(f"Scanning model files: {args.models_path}")
        model_data = model_scanner.collect(args.models_path)
        scanned    = model_data.get("files_scanned", [])
        _log(f"{len(scanned)} files scanned")
        all_issues += schema_rules.analyze(model_data)
        all_issues += index_rules.analyze(model_data)

    # Step 5: Terminal output
    cli_reporter.report(all_issues, source_label=source_label)

    # Step 6: Markdown report prompt
    _handle_report_prompt(all_issues, source_label, args)


def _handle_report_prompt(issues, source_label, args):
    """
    Developer se poochho: Markdown report save karein?
    --save-report  → seedha save, no prompt
    --no-report    → skip entirely
    default        → interactive prompt
    """
    if args.no_report:
        return

    if args.save_report:
        _save_md_report(issues, source_label)
        return

    # Interactive prompt
    print()
    print("─" * 50)
    try:
        answer = input("  Markdown (.md) report file save karein? (yes/no): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  [report] Non-interactive mode — report skip.")
        return

    if answer in ("yes", "y"):
        _save_md_report(issues, source_label)
    else:
        print("  Report save nahi ki.\n")


def _save_md_report(issues, source_label):
    """Generate + save, user ko full path dikhao."""
    print()
    try:
        content  = md_reporter.generate(issues, source_label=source_label)
        filepath = md_reporter.save(content)
        print(f"  ✅ Report saved at: {filepath}")
        print()
    except RuntimeError as e:
        _err(f"Report save nahi ho saki:\n  {e}")


def _log(msg):
    print(f"[pg-advisor] {msg}")

def _err(msg):
    print(f"[pg-advisor] ERROR: {msg}", file=sys.stderr)


if __name__ == "__main__":
    main()