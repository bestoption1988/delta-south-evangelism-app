"""
Read-only preflight for the current SQLite-to-Supabase migration.

This script does NOT create schemas, create tables, or modify records.
It checks source integrity, source schema, destination schema, and
generates a local JSON report.
"""

import getpass
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_DB = ROOT / "data" / "evangelism.db"
BACKUP_DB = ROOT / "data" / "backups" / (
    "evangelism_pre_migration_20261018_233106.db"
)
TARGET_SCHEMA = "mcn_migration_fresh_20261018"

REPORT_DIR = ROOT / "data" / "backups"
REPORT_PATH = REPORT_DIR / "current_migration_preflight.json"


def inspect_sqlite(path):
    if not path.is_file():
        raise RuntimeError(f"Required SQLite file is missing: {path}")

    connection = sqlite3.connect(
        f"file:{path.resolve()}?mode=ro",
        uri=True,
    )

    try:
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError(
                f"SQLite integrity check failed for {path}: {integrity}"
            )

        tables = {}
        for (table_name,) in connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """):
            quoted = '"' + table_name.replace('"', '""') + '"'

            columns = connection.execute(
                f"PRAGMA table_info({quoted})"
            ).fetchall()

            foreign_keys = connection.execute(
                f"PRAGMA foreign_key_list({quoted})"
            ).fetchall()

            count = connection.execute(
                f"SELECT COUNT(*) FROM {quoted}"
            ).fetchone()[0]

            tables[table_name] = {
                "row_count": count,
                "columns": [
                    {
                        "name": column[1],
                        "type": column[2] or "",
                        "not_null": bool(column[3]),
                        "default": column[4],
                        "primary_key_position": column[5],
                    }
                    for column in columns
                ],
                "foreign_keys": [
                    {
                        "referenced_table": fk[2],
                        "source_column": fk[3],
                        "referenced_column": fk[4],
                    }
                    for fk in foreign_keys
                ],
            }

        foreign_key_violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        return {
            "path": str(path.relative_to(ROOT)),
            "size_bytes": path.stat().st_size,
            "integrity": integrity,
            "table_count": len(tables),
            "tables": tables,
            "foreign_key_violation_count": len(
                foreign_key_violations
            ),
            "foreign_key_violations": [
                list(row) for row in foreign_key_violations
            ],
        }
    finally:
        connection.close()


def main():
    print("===== CURRENT SQLITE TO SUPABASE PREFLIGHT =====")
    print("Mode: READ ONLY")
    print("Destination schema:", TARGET_SCHEMA)

    source = inspect_sqlite(SOURCE_DB)
    backup = inspect_sqlite(BACKUP_DB)

    print("\nCurrent SQLite integrity:", source["integrity"])
    print("Current SQLite tables:", source["table_count"])
    print("Current SQLite rows:", sum(
        table["row_count"] for table in source["tables"].values()
    ))

    print("\nBackup integrity:", backup["integrity"])
    print("Backup tables:", backup["table_count"])
    print("Backup rows:", sum(
        table["row_count"] for table in backup["tables"].values()
    ))

    source_signature = {
        name: {
            "row_count": table["row_count"],
            "columns": table["columns"],
        }
        for name, table in source["tables"].items()
    }
    backup_signature = {
        name: {
            "row_count": table["row_count"],
            "columns": table["columns"],
        }
        for name, table in backup["tables"].items()
    }

    print(
        "\nSource and backup table definitions/counts match:",
        source_signature == backup_signature,
    )

    print("\n===== SUPABASE DESTINATION CHECK =====")
    password = getpass.getpass(
        "Supabase database password (hidden): "
    )

    os.environ.update({
        "SUPABASE_DB_HOST": (
            "aws-1-eu-central-1.pooler.supabase.com"
        ),
        "SUPABASE_DB_PORT": "5432",
        "SUPABASE_DB_NAME": "postgres",
        "SUPABASE_DB_USER": "postgres.cmhleervgxnmceyiepba",
        "SUPABASE_DB_PASSWORD": password,
        "SUPABASE_DB_SCHEMA": TARGET_SCHEMA,
    })

    connection = None
    destination = {}

    try:
        from postgres_adapter import connect_postgres

        connection = connect_postgres()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            ORDER BY schema_name
        """)
        existing_schemas = [row[0] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """, (TARGET_SCHEMA,))
        existing_test_tables = [
            row[0] for row in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = %s
        """, (TARGET_SCHEMA,))
        fresh_schema_exists = cursor.fetchone() is not None

        destination = {
            "existing_schemas": existing_schemas,
            "existing_test_table_count": len(existing_test_tables),
            "existing_test_tables": existing_test_tables,
            "fresh_schema": TARGET_SCHEMA,
            "fresh_schema_already_exists": fresh_schema_exists,
        }

        print("Existing migration-test tables:",
              len(existing_test_tables))
        print("Fresh destination schema already exists:",
              fresh_schema_exists)

    finally:
        if connection is not None:
            connection.close()
        os.environ.pop("SUPABASE_DB_PASSWORD", None)

    report = {
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "mode": "read_only_preflight",
        "source": source,
        "backup": backup,
        "destination": destination,
        "checks": {
            "source_integrity_ok": source["integrity"] == "ok",
            "backup_integrity_ok": backup["integrity"] == "ok",
            "source_table_count_is_51": (
                source["table_count"] == 51
            ),
            "backup_table_count_is_51": (
                backup["table_count"] == 51
            ),
            "source_backup_schema_and_counts_match": (
                source_signature == backup_signature
            ),
            "source_foreign_key_violations": (
                source["foreign_key_violation_count"]
            ),
            "backup_foreign_key_violations": (
                backup["foreign_key_violation_count"]
            ),
            "fresh_destination_available": (
                not destination["fresh_schema_already_exists"]
            ),
        },
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )

    print("\n===== PREFLIGHT RESULTS =====")
    for name, value in report["checks"].items():
        print(f"{name}: {value}")

    print("\nReport saved to:", REPORT_PATH.relative_to(ROOT))
    print("No PostgreSQL schemas or records were changed.")
    print("No SQLite records were changed.")


if __name__ == "__main__":
    main()
