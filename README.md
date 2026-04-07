# pg-advisor

**PostgreSQL schema & query advisor** — rule-based, no AI, fully deterministic.

Connect karo apna DB, aur ye batayega kya galat hai aur kaise fix karo.

```
╭──────────────────────────── pg-advisor Report ────────────────────────────╮
│ localhost/mydb                                                             │
│ ❌ 3 critical  ⚠  4 warnings  ℹ  5 info  (12 total)                       │
╰────────────────────────────────────────────────────────────────────────────╯

━━━ Table: orders ━━━
  ❌ CRITICAL  FK_WITHOUT_INDEX.user_id
    'orders.user_id' → 'users' FK hai lekin index nahi — JOINs slow honge.
    → CREATE INDEX idx_orders_user_id ON orders(user_id);

  ❌ CRITICAL  FLOAT_FOR_MONEY.total
    'orders.total' FLOAT use kar raha hai — precision errors ho sakte hain.
    → ALTER TABLE orders ALTER COLUMN total TYPE NUMERIC(12,2);

  ⚠  WARNING   DUPLICATE_INDEX
    columns ['total'] ke liye 2 indexes hain — ek waste hai.
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

**Model files bhi scan karo (SQLAlchemy / Django / SQL):**
```bash
pg-advisor analyze --models-path ./models/
pg-advisor analyze --models-path .        # poora project scan
```

**Query stats skip karo:**
```bash
pg-advisor analyze --skip-queries
```

---

## Kya kya check karta hai

### Schema Rules

| Rule | Kya pakdta hai | Severity |
|------|----------------|----------|
| `MISSING_PK` | Table bina primary key ke | ❌ Critical |
| `FLOAT_FOR_MONEY` | `price`, `balance`, `total` columns FLOAT mein | ❌ Critical |
| `FK_WITHOUT_INDEX` | Foreign key column pe index nahi | ❌ Critical |
| `NULLABLE_PK` | Primary key nullable mark hai | ❌ Critical |
| `MISSING_CREATED_AT` | `created_at` column nahi hai | ⚠ Warning |
| `BOOL_AS_INT` | `is_active`, `has_access` INTEGER mein stored | ⚠ Warning |
| `GOD_TABLE` | 30+ columns wali table — split karo | ⚠ Warning |
| `MISSING_NOT_NULL` | Email, name, status nullable hain | ℹ Info |
| `MISSING_UPDATED_AT` | `updated_at` column nahi hai | ℹ Info |

### Index Rules

| Rule | Kya pakdta hai | Severity |
|------|----------------|----------|
| `DUPLICATE_INDEX` | Same columns pe 2+ indexes | ⚠ Warning |
| `UNUSED_INDEX` | Index kabhi use nahi hua (live DB se) | ⚠ Warning |
| `LOW_CARDINALITY_INDEX` | Boolean/status column pe index | ℹ Info |

### Query Rules *(pg_stat_statements required)*

| Rule | Kya pakdta hai | Severity |
|------|----------------|----------|
| `SLOW_QUERY` | 500ms+ average execution time | ❌ Critical |
| `HIGH_FREQUENCY_QUERY` | 1000+ calls — cache karo | ⚠ Warning |
| `SELECT_STAR` | `SELECT *` use ho raha hai | ⚠ Warning |

---

## Model File Scanning

DB connect kiye bina bhi model files se issues pakad sakta hai:

**SQLAlchemy:**
```python
class Order(Base):
    __tablename__ = "orders"
    total = Column(Float)        # ← FLOAT_FOR_MONEY flag karega
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

Query analysis ke liye ye extension chahiye:

```sql
-- postgresql.conf mein add karo:
-- shared_preload_libraries = 'pg_stat_statements'

-- Phir DB mein run karo:
CREATE EXTENSION pg_stat_statements;
```

Agar available nahi hai to `--skip-queries` flag use karo — baki sab checks chalte rahenge.

---

## Project Structure

```
pg_advisor/
├── connectors/
│   └── postgres.py       # DB connection, URL resolver
├── collectors/
│   ├── db_schema.py      # Live DB se schema fetch
│   └── model_scanner.py  # SQLAlchemy/Django/SQL file scan
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
- `psycopg2-binary`, `rich`, `python-dotenv` (pip install pe auto-install hote hain)

---

## License

MIT