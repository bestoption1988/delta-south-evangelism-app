import sqlite3
import json
import os
from datetime import datetime

DB = "data/backups/evangelism_before_postgres_20261014_070817.db"
OUT_DIR = "data/backups"

if not os.path.isfile(DB):
    raise SystemExit(f"STOP: Database backup not found: {DB}")

os.makedirs(OUT_DIR, exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output = os.path.join(OUT_DIR, f"postgres_data_export_{stamp}.json")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

try:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise SystemExit(f"STOP: SQLite integrity check failed: {integrity}")

    tables = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """).fetchall()

    export = {
        "source": os.path.basename(DB),
        "integrity": integrity,
        "tables": {}
    }

    total_rows = 0

    for (table,) in tables:
        # Table names originate from SQLite's own schema.
        quoted = '"' + table.replace('"', '""') + '"'
        rows = conn.execute(f"SELECT * FROM {quoted}").fetchall()

        export["tables"][table] = {
            "columns": [item["name"] for item in conn.execute(
                f"PRAGMA table_info({quoted})"
            ).fetchall()],
            "rows": [dict(row) for row in rows]
        }

        total_rows += len(rows)
        print(f"{table}: {len(rows)} rows")

    with open(output, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    print("\nEXPORT SUCCESS")
    print("Tables:", len(export["tables"]))
    print("Total rows:", total_rows)
    print("File:", output)
    print("Bytes:", os.path.getsize(output))

finally:
    conn.close()
