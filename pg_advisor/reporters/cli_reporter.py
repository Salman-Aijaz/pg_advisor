"""
reporters/cli_reporter.py

Terminal pe colored output deta hai.
rich library use karta hai — professional look.

Output format:
  ━━━ Table: users ━━━━━━━━━━━━━━
  ❌ CRITICAL  FLOAT_FOR_MONEY
     balance column FLOAT use kar raha hai
     Fix: ALTER TABLE users ALTER COLUMN balance TYPE NUMERIC(12,2);

  ⚠  WARNING   FK_WITHOUT_INDEX
     ...
"""

import sys

try:
    from rich.console import Console  
    from rich.table   import Table   
    from rich.panel   import Panel    
    from rich.text    import Text    
    from rich         import box    


    console = Console(stderr=False)
    _RICH = True
except ImportError:
    _RICH = False
    console=None

from pg_advisor.analyzers.schema_rules import Issue



# ─────────────────────────────────────────────
# Severity config
# ─────────────────────────────────────────────

SEVERITY_CONFIG = {
    "critical": {"icon": "❌", "color": "bold red",    "label": "CRITICAL"},
    "warning":  {"icon": "⚠ ", "color": "bold yellow", "label": "WARNING "},
    "info":     {"icon": "ℹ ", "color": "bold cyan",   "label": "INFO    "},
}


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def report(issues: list[Issue], source_label: str = "Analysis") -> None:
    """
    Issues ki list lo, terminal pe colored report print karo.
    """
    if not _RICH:
        _plain_report(issues, source_label)
        return

    if not issues:
        console.print(f"\n[bold green]✅ Koi issue nahi mila! Database clean lag raha hai.[/bold green]\n")
        return

    # Group by table
    by_table: dict[str, list[Issue]] = {}
    for issue in issues:
        by_table.setdefault(issue.table, []).append(issue)

    # Header
    total     = len(issues)
    criticals = sum(1 for i in issues if i.severity == "critical")
    warnings  = sum(1 for i in issues if i.severity == "warning")
    infos     = sum(1 for i in issues if i.severity == "info")

    console.print()
    console.print(Panel(
        f"[bold]{source_label}[/bold]\n"
        f"[red]❌ {criticals} critical[/red]  "
        f"[yellow]⚠  {warnings} warnings[/yellow]  "
        f"[cyan]ℹ  {infos} info[/cyan]  "
        f"[dim]({total} total)[/dim]",
        title="[bold white]pg-advisor Report[/bold white]",
        border_style="bright_black",
    ))

    # Per-table output
    for table_name, table_issues in sorted(by_table.items()):
        _print_table_section(table_name, table_issues)

    # Summary footer
    _print_summary(issues)


def _print_table_section(table_name: str, issues: list[Issue]) -> None:
    """Ek table ke saare issues print karo."""

    # Table header
    console.print(f"\n[bold white]━━━ Table: [cyan]{table_name}[/cyan] ━━━[/bold white]")

    for issue in sorted(issues, key=lambda i: _severity_order(i.severity)):
        cfg = SEVERITY_CONFIG.get(issue.severity, SEVERITY_CONFIG["info"])

        # Severity badge + rule ID
        col_str = f"[dim].{issue.column}[/dim]" if issue.column else ""
        console.print(
            f"  [{cfg['color']}]{cfg['icon']} {cfg['label']}[/{cfg['color']}]  "
            f"[bright_black]{issue.rule}[/bright_black]{col_str}"
        )

        # Message
        console.print(f"    [white]{issue.message}[/white]")

        # Fix — dimmed green
        fix_lines = issue.fix.split("\n")
        for line in fix_lines:
            console.print(f"    [dim green]→ {line.strip()}[/dim green]")

        console.print()


def _print_summary(issues: list[Issue]) -> None:
    """Bottom summary table."""
    tbl = Table(
        box         = box.SIMPLE,
        show_header = True,
        header_style= "bold white",
        border_style= "bright_black",
        title       = "[bold]Issue Breakdown by Rule[/bold]",
    )
    tbl.add_column("Rule",     style="bright_black")
    tbl.add_column("Severity", style="bold")
    tbl.add_column("Count",    justify="right")

    rule_counts: dict[tuple, int] = {}
    for issue in issues:
        key = (issue.rule, issue.severity)
        rule_counts[key] = rule_counts.get(key, 0) + 1

    for (rule, severity), count in sorted(rule_counts.items()):
        cfg   = SEVERITY_CONFIG.get(severity, SEVERITY_CONFIG["info"])
        color = cfg["color"]
        tbl.add_row(rule, f"[{color}]{cfg['icon']} {severity}[/{color}]", str(count))

    console.print(tbl)
    console.print()


# ─────────────────────────────────────────────
# Fallback — plain text (no rich)
# ─────────────────────────────────────────────

def _plain_report(issues: list[Issue], source_label: str) -> None:
    """Agar rich install nahi to plain output."""
    icons = {"critical": "❌", "warning": "⚠ ", "info": "ℹ "}
    print(f"\n=== {source_label} — {len(issues)} issues ===\n")
    for i in issues:
        icon = icons.get(i.severity, "•")
        col  = f".{i.column}" if i.column else ""
        print(f"{icon} [{i.severity.upper()}] {i.table}{col} — {i.rule}")
        print(f"   {i.message}")
        print(f"   Fix: {i.fix}")
        print()


# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────

def _severity_order(s: str) -> int:
    return {"critical": 0, "warning": 1, "info": 2}.get(s, 9)