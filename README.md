# pg-advisor

**PostgreSQL schema & query advisor** — rule-based, no AI, fully deterministic.

Connect your database, and it will tell you what's wrong and how to fix it.

```
╭──────────────────────────── pg-advisor Report ────────────────────────────╮
│ localhost/mydb                                                             │
│ ❌ 3 critical  ⚠  4 warnings  ℹ  5 info  (12 total)                       │
╰────────────────────────────────────────────────────────────────────────────╯

━━━ Table: orders ━━━
  ❌ CRITICAL  FK_WITHOUT_INDEX.user_id
    'orders.user_id' has a foreign key to 'users' but no index — JOINs will be slow.
    → CREATE INDEX idx_orders_user_id ON orders(user_id);

  ❌ CRITICAL  FLOAT_FOR_MONEY.total
    'orders.total' uses FLOAT type — precision errors may occur.
    → ALTER TABLE orders ALTER COLUMN total TYPE NUMERIC(12,2);

  ⚠  WARNING   DUPLICATE_INDEX
    2 indexes exist for columns ['total'] — one is redundant.
    → DROP INDEX idx_orders_total2;
```

---

## Install

```bash
pip install pg-advisor
```

---

## Quick Start

Run this after installing to check your PostgreSQL extension setup:

```bash
pg-advisor setup postgresql://user:pass@localhost:5432/mydb
```

Then run the full analysis:

```bash
pg-advisor analyze postgresql://user:pass@localhost:5432/mydb
```

---

## Extension Setup

pg-advisor uses three PostgreSQL extensions. Run `pg-advisor setup` to check which ones are available on your database.

| Extension | Type | Used for | Required? |
|-----------|------|----------|-----------|
| `pg_stat_activity` | Built-in | Live query monitoring, lock waits, connection pool | Auto-available |
| `pg_stat_statements` | Built-in, off by default | Slow queries, SELECT * detection, high-frequency queries | Optional |
| `hypopg` | Third-party | Confirms an index will actually improve query cost | Optional |

Missing extensions are skipped gracefully — pg-advisor will still run and report all other issues.

### Enabling pg_stat_statements

```sql
-- 1. Add to postgresql.conf:
shared_preload_libraries = 'pg_stat_statements'

-- 2. Restart PostgreSQL, then run in your database:
CREATE EXTENSION pg_stat_statements;
```

### Installing hypopg

```bash
# Ubuntu / Debian
sudo apt install postgresql-<version>-hypopg

# macOS (Homebrew)
brew install hypopg
```

```sql
-- Then in your database:
CREATE EXTENSION hypopg;
```

---

## Usage

**Option 1 — Direct URL:**
```bash
pg-advisor analyze postgresql://user:pass@localhost:5432/mydb
```

**Option 2 — Environment variable:**
```bash
export DATABASE_URL=postgresql://user:pass@localhost/mydb
pg-advisor analyze
```

**Option 3 — `.env` file:**
```ini
DATABASE_URL=postgresql://user:pass@localhost/mydb
```
```bash
pg-advisor analyze
```

**Scan model files too (SQLAlchemy / Django / SQL):**
```bash
pg-advisor analyze --models-path ./models/
pg-advisor analyze --models-path .        # scan entire project
```

**Skip specific checks:**
```bash
pg-advisor analyze --skip-queries     # skip pg_stat_statements checks
pg-advisor analyze --skip-hypopg      # skip hypothetical index testing
pg-advisor analyze --skip-activity    # skip live connection monitoring
```

---

## Output & Reports

After every run, pg-advisor prints a colored summary to the terminal. It then prompts you to save a Markdown report:

```
──────────────────────────────────────────────────
  Save Markdown (.md) report? (yes/no):
```

Answer `yes` and the file is written immediately:

```
  ✅ Report saved at: /your/project/pgadvisor_report/pg_advisor_report_20260408_143022.md
```

**Skip the prompt with flags:**

```bash
pg-advisor analyze ... --save-report   # always save, no prompt
pg-advisor analyze ... --no-report     # never save, no prompt (CI/CD)
```

### Report folder & file naming

| Detail | Value |
|--------|-------|
| Folder | `pgadvisor_report/` — auto-created in your current working directory on first run |
| Filename | `pg_advisor_report_YYYYMMDD_HHMMSS.md` |
| Example | `pgadvisor_report/pg_advisor_report_20260408_143022.md` |
| Encoding | UTF-8 |

The folder is created automatically — no setup needed. Each run produces a uniquely timestamped file; existing reports are never overwritten.

### What the Markdown report contains

- **Summary header** — database, timestamp, critical / warning / info counts
- **Issue summary table** — every issue across all tables in one place
- **Per-table sections** — each issue with severity, message, and a ready-to-run SQL fix block
- **Rule reference** — full list of all rules and what they check

---

## What does it check?

### Schema Rules

| Rule | What it detects | Severity |
|------|----------------|----------|
| `MISSING_PK` | Table without primary key | ❌ Critical |
| `FLOAT_FOR_MONEY` | `price`, `balance`, `total` columns using FLOAT type | ❌ Critical |
| `FK_WITHOUT_INDEX` | No index on foreign key column | ❌ Critical |
| `NULLABLE_PK` | Primary key marked as nullable | ❌ Critical |
| `MISSING_CREATED_AT` | `created_at` column is missing | ⚠ Warning |
| `BOOL_AS_INT` | `is_active`, `has_access` stored as INTEGER | ⚠ Warning |
| `GOD_TABLE` | Table with 30+ columns — consider splitting | ⚠ Warning |
| `MISSING_NOT_NULL` | Email, name, status columns are nullable | ℹ Info |
| `MISSING_UPDATED_AT` | `updated_at` column is missing | ℹ Info |

### Index Rules

| Rule | What it detects | Severity |
|------|----------------|----------|
| `DUPLICATE_INDEX` | 2+ indexes on the same columns | ⚠ Warning |
| `UNUSED_INDEX` | Index never used (detected from live DB) | ⚠ Warning |
| `LOW_CARDINALITY_INDEX` | Index on boolean/status column | ℹ Info |

### Query Rules *(requires pg_stat_statements)*

| Rule | What it detects | Severity |
|------|----------------|----------|
| `SLOW_QUERY` | Average execution time ≥ 500ms | ❌ Critical |
| `HIGH_FREQUENCY_QUERY` | 1000+ calls — consider caching | ⚠ Warning |
| `SELECT_STAR` | Use of `SELECT *` in queries | ⚠ Warning |

### Activity Rules *(pg_stat_activity — built-in)*

| Rule | What it detects | Severity |
|------|----------------|----------|
| `LONG_RUNNING_QUERY` | Query running for 30s+ | ❌ Critical |
| `IDLE_IN_TRANSACTION` | Connection idle-in-transaction for 60s+ | ❌ Critical |
| `LOCK_WAIT` | Query blocked waiting for a lock | ❌ Critical |
| `CONNECTION_POOL_PRESSURE` | 80%+ of max_connections in use | ⚠ Warning |

### Hypothetical Index Rules *(requires hypopg)*

| Rule | What it detects | Severity |
|------|----------------|----------|
| `HYPOPG_INDEX_CONFIRMED` | Index verified to reduce query cost | ❌ Critical |

---

## Model File Scanning

Can detect issues from model files without connecting to the database:

**SQLAlchemy:**
```python
class Order(Base):
    __tablename__ = "orders"
    total = Column(Float)        # ← will flag FLOAT_FOR_MONEY
```

**Django ORM:**
```python
class Order(models.Model):
    total = models.FloatField()  # ← same flag
```

**Plain SQL:**
```sql
CREATE TABLE orders (
    total FLOAT                  -- ← same flag
);
```

---

## Project Structure

```
pg_advisor/
├── connectors/
│   └── postgres.py          # DB connection, URL resolver
├── collectors/
│   ├── db_schema.py         # Fetch schema from live DB
│   └── model_scanner.py     # Scan SQLAlchemy/Django/SQL files
├── analyzers/
│   ├── schema_rules.py      # Schema issues (9 rules)
│   ├── index_rules.py       # Index issues (3 rules)
│   ├── query_rules.py       # Query issues (3 rules)
│   ├── activity_rules.py    # Live monitoring (4 rules)
│   └── hypopg_rules.py      # Hypothetical index testing (1 rule)
├── reporters/
│   ├── cli_reporter.py      # Colored terminal output
│   └── md_reporter.py       # Markdown report generator
└── cli.py                   # Entry point
```

---

## Requirements

- Python 3.11+
- PostgreSQL 12+
- `psycopg2-binary`, `rich`, `python-dotenv` (auto-installed via pip)

---

## License

MIT