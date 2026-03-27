"""
collectors/model_scanner.py

Model files ko scan karta hai — bina DB connect kiye:
  - SQLAlchemy  (class User(Base): ...)
  - Django ORM  (class User(models.Model): ...)
  - Plain SQL   (CREATE TABLE ... )

Automatically detect karta hai format.
Returns: same unified dict format as db_schema.py
"""

import ast
import re
from pathlib import Path


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def collect(path: str) -> dict:
    """
    Ek file ya folder path do.
    Automatically scan karega sab model files.

    Usage:
        collect("./models.py")
        collect("./models/")
        collect(".")           # poora project scan
    """
    target = Path(path)
    all_tables = {}

    if target.is_file():
        files = [target]
    else:
        # Folder mein se relevant files dhundo
        files = _find_model_files(target)

    for f in files:
        fmt = _detect_format(f)
        if fmt == "sqlalchemy":
            tables = _parse_sqlalchemy(f)
        elif fmt == "django":
            tables = _parse_django(f)
        elif fmt == "sql":
            tables = _parse_sql(f)
        else:
            continue  # skip unknown files

        # Merge into all_tables
        for tbl, data in tables.items():
            if tbl not in all_tables:
                all_tables[tbl] = data
            else:
                # Same table multiple files mein — columns merge karo
                all_tables[tbl]["columns"].update(data["columns"])

    return {
        "tables": all_tables,
        "source": "model_files",
        "files_scanned": [str(f) for f in files],
    }


# ─────────────────────────────────────────────
# File finder
# ─────────────────────────────────────────────

def _find_model_files(folder: Path) -> list[Path]:
    """
    Folder mein se model files dhundo.
    Naming patterns: models.py, schema.py, entities.py, *.sql
    """
    patterns = [
        "**/models.py",
        "**/model.py",
        "**/schema.py",
        "**/schemas.py",
        "**/entities.py",
        "**/db_models.py",
        "**/*.sql",
    ]
    found = []
    seen  = set()

    # Skip these folders
    skip = {"venv", ".venv", "env", "node_modules",
            "__pycache__", ".git", "migrations"}

    for pattern in patterns:
        for f in folder.glob(pattern):
            if f in seen:
                continue
            # Skip ignored folders
            if any(part in skip for part in f.parts):
                continue
            seen.add(f)
            found.append(f)

    return sorted(found)


# ─────────────────────────────────────────────
# Format detector
# ─────────────────────────────────────────────

def _detect_format(filepath: Path) -> str:
    """
    File content dekh ke format decide karo.
    Returns: "sqlalchemy" | "django" | "sql" | "unknown"
    """
    if filepath.suffix == ".sql":
        return "sql"

    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "unknown"

    # SQLAlchemy signals
    if any(sig in content for sig in [
        "from sqlalchemy", "import Column", "declarative_base",
        "DeclarativeBase", "mapped_column", "Mapped["
    ]):
        return "sqlalchemy"

    # Django signals
    if any(sig in content for sig in [
        "from django.db", "models.Model", "models.CharField",
        "models.IntegerField", "models.ForeignKey"
    ]):
        return "django"

    return "unknown"


# ─────────────────────────────────────────────
# SQLAlchemy parser (AST-based)
# ─────────────────────────────────────────────

# Type mapping: SQLAlchemy → PostgreSQL types
_SA_TYPE_MAP = {
    "Integer":    "integer",
    "BigInteger": "bigint",
    "String":     "varchar",
    "Text":       "text",
    "Float":      "float",        # ← analyzer flag karega
    "Numeric":    "numeric",
    "Boolean":    "boolean",
    "DateTime":   "timestamp",
    "Date":       "date",
    "Time":       "time",
    "JSON":       "json",
    "JSONB":      "jsonb",
    "UUID":       "uuid",
    "LargeBinary":"bytea",
}

def _parse_sqlalchemy(filepath: Path) -> dict:
    """AST se SQLAlchemy models parse karo."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
        tree   = ast.parse(source)
    except Exception:
        return {}

    tables = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        # Check karo ye Base se inherit karta hai
        bases = [_get_name(b) for b in node.bases]
        if not any("Base" in b or "Model" in b for b in bases):
            continue

        table_name = _extract_tablename_sa(node, source)
        if not table_name:
            table_name = node.name.lower() + "s"  # guess: User → users

        columns     = {}
        primary_keys = []
        foreign_keys = []
        indexes      = []

        for item in node.body:
            # Assignment: email = Column(String, ...)
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    col_name = target.id
                    col_info = _parse_sa_column(item.value)
                    if col_info:
                        columns[col_name] = col_info
                        if col_info["pk"]:
                            primary_keys.append(col_name)
                        if col_info["fk"]:
                            foreign_keys.append({
                                "column":     col_name,
                                "ref_table":  col_info["fk"],
                                "ref_column": "id",
                            })

            # Annotated: email: Mapped[str] = mapped_column(...)
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                col_name = item.target.id
                if item.value:
                    col_info = _parse_sa_column(item.value)
                    if col_info:
                        columns[col_name] = col_info
                        if col_info["pk"]:
                            primary_keys.append(col_name)
                        if col_info["fk"]:
                            foreign_keys.append({
                                "column":     col_name,
                                "ref_table":  col_info["fk"],
                                "ref_column": "id",
                            })

        if columns:
            tables[table_name] = {
                "columns":      columns,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "indexes":      indexes,
                "constraints":  [],
            }

    return tables


def _parse_sa_column(node) -> dict | None:
    """
    Column(...) ya mapped_column(...) call parse karo.
    Returns column info dict ya None.
    """
    if not isinstance(node, ast.Call):
        return None

    func_name = _get_name(node.func)
    if func_name not in ("Column", "mapped_column"):
        return None

    col_type  = "unknown"
    nullable  = True
    pk        = False
    fk        = None
    default   = None

    # Positional args — pehla arg usually type hota hai
    for arg in node.args:
        name = _get_name(arg)
        if name in _SA_TYPE_MAP:
            col_type = _SA_TYPE_MAP[name]
        elif name == "ForeignKey" and isinstance(arg, ast.Call):
            # ForeignKey("users.id") → ref_table = "users"
            if arg.args and isinstance(arg.args[0], ast.Constant):
                fk_target = str(arg.args[0].value)
                fk = fk_target.split(".")[0]  # "users.id" → "users"

    # Keyword args — nullable=False, primary_key=True, etc.
    for kw in node.keywords:
        if kw.arg == "primary_key" and isinstance(kw.value, ast.Constant):
            pk = bool(kw.value.value)
        elif kw.arg == "nullable" and isinstance(kw.value, ast.Constant):
            nullable = bool(kw.value.value)
        elif kw.arg == "default" and isinstance(kw.value, ast.Constant):
            default = kw.value.value

    return {
        "type":     col_type,
        "nullable": nullable,
        "default":  default,
        "pk":       pk,
        "fk":       fk,
    }


def _extract_tablename_sa(class_node, source: str) -> str | None:
    """__tablename__ = 'users' dhundo class mein."""
    for item in class_node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id == "__tablename__":
                    if isinstance(item.value, ast.Constant):
                        return item.value.value
    return None


# ─────────────────────────────────────────────
# Django parser (AST-based)
# ─────────────────────────────────────────────

_DJANGO_TYPE_MAP = {
    "AutoField":         "integer",
    "BigAutoField":      "bigint",
    "IntegerField":      "integer",
    "BigIntegerField":   "bigint",
    "CharField":         "varchar",
    "TextField":         "text",
    "FloatField":        "float",       # ← flag karega analyzer
    "DecimalField":      "numeric",
    "BooleanField":      "boolean",
    "DateTimeField":     "timestamp",
    "DateField":         "date",
    "TimeField":         "time",
    "JSONField":         "jsonb",
    "UUIDField":         "uuid",
    "BinaryField":       "bytea",
    "ForeignKey":        "integer",     # FK = integer col
    "OneToOneField":     "integer",
    "ManyToManyField":   None,          # skip — junction table hai
}

def _parse_django(filepath: Path) -> dict:
    """AST se Django models parse karo."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
        tree   = ast.parse(source)
    except Exception:
        return {}

    tables = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        bases = [_get_name(b) for b in node.bases]
        if not any("Model" in b for b in bases):
            continue

        # Django mein table name: appname_classname (lowercase)
        # Hum sirf classname use karenge
        table_name = node.name.lower()

        columns      = {}
        primary_keys = ["id"]  # Django auto-adds id PK
        foreign_keys = []

        # Auto id column
        columns["id"] = {
            "type": "integer", "nullable": False,
            "default": None, "pk": True, "fk": None,
        }

        for item in node.body:
            if not isinstance(item, ast.Assign):
                continue
            for target in item.targets:
                if not isinstance(target, ast.Name):
                    continue
                col_name  = target.id
                col_info  = _parse_django_field(item.value)
                if col_info is None:
                    continue  # ManyToMany — skip
                if col_info:
                    columns[col_name] = col_info
                    if col_info.get("fk"):
                        foreign_keys.append({
                            "column":     col_name + "_id",
                            "ref_table":  col_info["fk"],
                            "ref_column": "id",
                        })

        if len(columns) > 1:  # sirf id se zyada ho
            tables[table_name] = {
                "columns":      columns,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "indexes":      [],
                "constraints":  [],
            }

    return tables


def _parse_django_field(node) -> dict | None:
    """models.CharField(...) parse karo."""
    if not isinstance(node, ast.Call):
        return {}

    field_name = _get_name(node.func)
    pg_type    = _DJANGO_TYPE_MAP.get(field_name)

    if field_name == "ManyToManyField":
        return None  # skip entirely

    if pg_type is None and field_name not in _DJANGO_TYPE_MAP:
        return {}

    nullable = False
    fk       = None
    default  = None

    for kw in node.keywords:
        if kw.arg in ("null", "blank") and isinstance(kw.value, ast.Constant):
            if kw.value.value:
                nullable = True
        elif kw.arg == "default" and isinstance(kw.value, ast.Constant):
            default = kw.value.value
        elif kw.arg == "to" and isinstance(kw.value, ast.Constant):
            fk = kw.value.value.lower()

    # ForeignKey("ModelName") — positional arg
    if field_name in ("ForeignKey", "OneToOneField") and node.args:
        first = node.args[0]
        if isinstance(first, ast.Constant):
            fk = str(first.value).lower()
        elif isinstance(first, ast.Name):
            fk = first.id.lower()

    return {
        "type":     pg_type or "unknown",
        "nullable": nullable,
        "default":  default,
        "pk":       False,
        "fk":       fk,
    }


# ─────────────────────────────────────────────
# Plain SQL parser (regex-based)
# ─────────────────────────────────────────────

_SQL_TYPE_MAP = {
    r"\bint\b|\binteger\b":          "integer",
    r"\bbigint\b":                   "bigint",
    r"\bserial\b":                   "integer",
    r"\bbigserial\b":                "bigint",
    r"\bvarchar\b|\bcharacter varying\b": "varchar",
    r"\btext\b":                     "text",
    r"\bfloat\b|\breal\b|\bdouble precision\b": "float",
    r"\bnumeric\b|\bdecimal\b":      "numeric",
    r"\bboolean\b|\bbool\b":         "boolean",
    r"\btimestamp\b":                "timestamp",
    r"\bdate\b":                     "date",
    r"\bjsonb\b":                    "jsonb",
    r"\bjson\b":                     "json",
    r"\buuid\b":                     "uuid",
}

def _parse_sql(filepath: Path) -> dict:
    """CREATE TABLE statements ko regex se parse karo."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {}

    tables = {}

    # Find all CREATE TABLE blocks
    pattern = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?\"?(\w+)\"?\s*\((.+?)\);",
        re.IGNORECASE | re.DOTALL
    )

    for match in pattern.finditer(content):
        table_name = match.group(1).lower()
        body       = match.group(2)

        columns      = {}
        primary_keys = []
        foreign_keys = []

        for line in body.split(","):
            line = line.strip()
            if not line:
                continue

            # Skip constraint lines
            if re.match(r"(CONSTRAINT|PRIMARY KEY|FOREIGN KEY|UNIQUE|CHECK)", line, re.I):
                # Extract inline PK
                pk_match = re.search(r"PRIMARY KEY\s*\(([^)]+)\)", line, re.I)
                if pk_match:
                    primary_keys = [c.strip().strip('"') for c in pk_match.group(1).split(",")]

                # Extract FK
                fk_match = re.search(
                    r"FOREIGN KEY\s*\((\w+)\)\s*REFERENCES\s+(\w+)\s*\((\w+)\)", line, re.I)
                if fk_match:
                    foreign_keys.append({
                        "column":     fk_match.group(1),
                        "ref_table":  fk_match.group(2),
                        "ref_column": fk_match.group(3),
                    })
                continue

            # Column line: col_name TYPE [NOT NULL] [DEFAULT x] [PRIMARY KEY]
            col_match = re.match(r'"?(\w+)"?\s+(.+)', line)
            if not col_match:
                continue

            col_name = col_match.group(1).lower()
            rest     = col_match.group(2).upper()

            # Detect type
            col_type = "unknown"
            orig     = col_match.group(2).lower()
            for pattern_str, pg_type in _SQL_TYPE_MAP.items():
                if re.search(pattern_str, orig, re.I):
                    col_type = pg_type
                    break

            nullable = "NOT NULL" not in rest
            pk       = "PRIMARY KEY" in rest

            if pk and col_name not in primary_keys:
                primary_keys.append(col_name)

            columns[col_name] = {
                "type":     col_type,
                "nullable": nullable,
                "default":  None,
                "pk":       pk,
                "fk":       None,
            }

        # Mark FK columns
        for fk in foreign_keys:
            col = fk["column"]
            if col in columns:
                columns[col]["fk"] = {
                    "ref_table":  fk["ref_table"],
                    "ref_column": fk["ref_column"],
                }

        if columns:
            tables[table_name] = {
                "columns":      columns,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "indexes":      [],
                "constraints":  [],
            }

    return tables


# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────

def _get_name(node) -> str:
    """AST node se name string nikalo."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Constant):
        return str(node.value)
    return ""