import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "evangelism.db"
BACKUP = ROOT / "data" / "backups" / "evangelism_pre_migration_20261018_233106.db"
OUT = ROOT / "data" / "backups" / "migration_plan_20261019.json"

def inspect(path):
    con = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Integrity failure: {path}")

        tables = {}
        for row in con.execute("""
            SELECT name, sql FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """):
            name = row["name"]
            qname = '"' + name.replace('"', '""') + '"'
            columns = con.execute(f"PRAGMA table_info({qname})").fetchall()
            foreign_keys = con.execute(f"PRAGMA foreign_key_list({qname})").fetchall()
            count = con.execute(f"SELECT COUNT(*) FROM {qname}").fetchone()[0]
            tables[name] = {
                "create_sql": row["sql"],
                "row_count": count,
                "columns": [
                    {
                        "name": c["name"],
                        "type": c["type"],
                        "not_null": bool(c["notnull"]),
                        "default": c["dflt_value"],
                        "primary_key_position": c["pk"],
                    }
                    for c in columns
                ],
                "foreign_keys": [
                    {
                        "column": fk["from"],
                        "referenced_table": fk["table"],
                        "referenced_column": fk["to"],
                        "on_update": fk["on_update"],
                        "on_delete": fk["on_delete"],
                    }
                    for fk in foreign_keys
                ],
            }

        objects = []
        for row in con.execute("""
            SELECT type, name, tbl_name, sql
            FROM sqlite_master
            WHERE type IN ('index', 'trigger', 'view')
              AND name NOT LIKE 'sqlite_%'
            ORDER BY type, name
        """):
            objects.append(dict(row))

        violations = con.execute("PRAGMA foreign_key_check").fetchall()
        return {
            "path": str(path.relative_to(ROOT)),
            "integrity": integrity,
            "table_count": len(tables),
            "total_rows": sum(t["row_count"] for t in tables.values()),
            "tables": tables,
            "indexes_triggers_views": objects,
            "foreign_key_violation_count": len(violations),
        }
    finally:
        con.close()

source = inspect(DB)
backup = inspect(BACKUP)

if source["table_count"] != 51 or source["total_rows"] != 956:
    raise SystemExit("STOP: source no longer matches the verified migration baseline.")

if source["tables"] != backup["tables"]:
    raise SystemExit("STOP: source and backup schema/data counts differ.")

if source["foreign_key_violation_count"] != 0:
    raise SystemExit("STOP: source has foreign-key violations.")

plan = {
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "mode": "LOCAL_READ_ONLY_MIGRATION_PLAN",
    "destination_schema": "mcn_migration_fresh_20261018",
    "source": source,
    "backup": {
        "path": backup["path"],
        "integrity": backup["integrity"],
        "table_count": backup["table_count"],
        "total_rows": backup["total_rows"],
    },
    "database_writes_performed": False,
    "production_cutover_performed": False,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(plan, indent=2), encoding="utf-8")

print("Migration plan saved:", OUT.relative_to(ROOT))
print("Source tables:", source["table_count"])
print("Source rows:", source["total_rows"])
print("Schema objects (indexes/triggers/views):", len(source["indexes_triggers_views"]))
print("Foreign-key violations:", source["foreign_key_violation_count"])
print("Backup tables:", backup["table_count"])
print("Backup rows:", backup["total_rows"])
print("Supabase modified: No")
print("Live application changed: No")
