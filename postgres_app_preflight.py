"""Read-only preflight for integrating Flask with PostgreSQL."""

import ast
from pathlib import Path

root = Path(__file__).resolve().parent
app_path = root / "app.py"
adapter_path = root / "postgres_adapter.py"

app_source = app_path.read_text(encoding="utf-8")
adapter_source = adapter_path.read_text(encoding="utf-8")

tree = ast.parse(app_source)

functions = {
    node.name: node.lineno
    for node in ast.walk(tree)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
}

print("========== POSTGRESQL APPLICATION PREFLIGHT ==========")

required_functions = (
    "db",
    "init_db",
    "ensure_column",
    "ensure_runtime_schema",
    "build_table_map",
    "ensure_member_passport_photo_schema",
    "ensure_member_care_case_assignment_schema",
    "ensure_member_care_timeline_schema",
    "ensure_member_care_attachment_schema",
)

for name in required_functions:
    if name in functions:
        print(f"FOUND: {name} at app.py:{functions[name]}")
    else:
        print(f"MISSING: {name}")

print("\n========== SQLITE-ONLY OPERATIONS ==========")

needles = (
    "sqlite3.connect",
    "sqlite3.Row",
    "executescript(",
    "PRAGMA ",
    "sqlite_master",
    "INSERT OR IGNORE",
    "COLLATE NOCASE",
)

for needle in needles:
    count = app_source.lower().count(needle.lower())
    print(f"{needle}: {count} occurrence(s)")

print("\n========== ADAPTER CAPABILITIES ==========")

for capability, present in (
    ("PostgreSQL connection wrapper", "class PostgreSQLConnection" in adapter_source),
    ("PostgreSQL row wrapper", "class PostgreSQLRow" in adapter_source),
    ("Placeholder conversion", "_convert_placeholders" in adapter_source),
    ("Generated-ID support", "execute_insert_returning_id" in adapter_source),
    ("Schema compatibility module", (root / "postgres_schema_compat.py").exists()),
    ("Database mode selector", (root / "database_mode.py").exists()),
    ("Connection factory", (root / "database_connection.py").exists()),
):
    print(f"{'FOUND' if present else 'MISSING'}: {capability}")

print("\nPREFLIGHT COMPLETE — no database was opened or modified.")
