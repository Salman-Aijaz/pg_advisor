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

**Skip query stats:**
```bash
pg-advisor analyze --skip-queries
```

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

## pg_stat_statements Setup

This extension is required for query analysis:

```sql
-- Add to postgresql.conf:
-- shared_preload_libraries = 'pg_stat_statements'

-- Then run in your database:
CREATE EXTENSION pg_stat_statements;
```

If not available, use the `--skip-queries` flag — all other checks will continue to work.

---

## Project Structure

```
pg_advisor/
├── connectors/
│   └── postgres.py       # DB connection, URL resolver
├── collectors/
│   ├── db_schema.py      # Fetch schema from live DB
│   └── model_scanner.py  # Scan SQLAlchemy/Django/SQL files
├── analyzers/
│   ├── schema_rules.py   # Schema issues (8 rules)
│   ├── index_rules.py    # Index issues (3 rules)
│   └── query_rules.py    # Query issues (3 rules)
├── reporters/
│   └── cli_reporter.py   # Colored terminal output
└── cli.py                # Entry point
```

---

## Requirements

- Python 3.10+
- PostgreSQL 12+
- `psycopg2-binary`, `rich`, `python-dotenv` (auto-installed via pip)

---

## License

MIT