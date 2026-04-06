"""
cli.py — pg-advisor ka main entry point

Usage:
  pg-advisor analyze postgresql://user:pass@localhost/mydb
  pg-advisor analyze --models-path ./models/
  pg-advisor analyze  (DATABASE_URL env se uthayega)
"""

import sys
import argparse

from pg_advisor.connecter.postgres import resolve_db_url
from pg_advisor.collectors  import db_schema, model_scanner
from pg_advisor.analyzers   import schema_rules, index_rules, query_rules
from pg_advisor.reporters   import cli_reporter


def main():
    parser = argparse.ArgumentParser(
        prog        = "pg-advisor",
        description = "PostgreSQL schema & query advisor",
    )
    sub = parser.add_subparsers(dest="command")

    # --- analyze command ---
    analyze_cmd = sub.add_parser("analyze", help="DB analyze karo")
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

    args = parser.parse_args()

    if args.command == "analyze":
        run_analyze(args)
    else:
        parser.print_help()


def run_analyze(args):
    all_issues = []

    # ── Step 1: DB URL resolve karo ──────────────
    try:
        db_url = resolve_db_url(args.db_url)
    except ValueError as e:
        print(str(e))
        sys.exit(1)

    print(f"\n[pg-advisor] Connecting to DB...")

    # ── Step 2: Live DB schema collect karo ──────
    try:
        print("[pg-advisor] Collecting schema from DB...")
        db_data = db_schema.collect(db_url)
        tables  = list(db_data["tables"].keys())
        print(f"[pg-advisor] {len(tables)} tables mili: {', '.join(tables)}")

        # Schema rules
        issues = schema_rules.analyze(db_data)
        all_issues += issues

        # Index rules (model-based)
        issues = index_rules.analyze(db_data)
        all_issues += issues

        # Index rules (live DB unused indexes)
        issues = index_rules.analyze_live(db_url)
        all_issues += issues

    except ConnectionError as e:
        print(f"\n[ERROR] DB connect nahi hua: {e}")
        sys.exit(1)

    # ── Step 3: Query stats (optional) ───────────
    if not args.skip_queries:
        print("[pg-advisor] Checking query stats...")
        issues = query_rules.analyze_live(db_url)
        all_issues += issues

    # ── Step 4: Model files scan (optional) ──────
    if args.models_path:
        print(f"[pg-advisor] Scanning model files: {args.models_path}")
        model_data = model_scanner.collect(args.models_path)
        scanned    = model_data.get("files_scanned", [])
        print(f"[pg-advisor] {len(scanned)} files scanned")

        issues = schema_rules.analyze(model_data)
        all_issues += issues

        issues = index_rules.analyze(model_data)
        all_issues += issues

    # ── Step 5: Report ────────────────────────────
    cli_reporter.report(all_issues, source_label=db_url.split("@")[-1])


if __name__ == "__main__":
    main()