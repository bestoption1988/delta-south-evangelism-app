import os
import sys
import json
import math
import hashlib
import sqlite3
import getpass
from decimal import Decimal

DB_PATH = "data/evangelism.db"
SCHEMA = "mcn_migration_fresh_20261018"


def normalize(value):
    if value is None:
        return ["null", None]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["number", str(value)]
    if isinstance(value, float):
        if math.isnan(value):
            return ["float", "NaN"]
        if math.isinf(value):
            return ["float", str(value)]
        return ["number", format(value, ".15g")]
    if isinstance(value, Decimal):
        return ["number", format(value.normalize(), "f")]
    if isinstance(value, bytes):
        return ["bytes", value.hex()]
    if isinstance(value, (bytearray, memoryview)):
        return ["bytes", bytes(value).hex()]
    if hasattr(value, "isoformat"):
        return ["datetime", value.isoformat()]
    return ["text", str(value)]


def row_digest(row):
    payload = json.dumps(
        [normalize(v) for v in row],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def quote_identifier(name):
    return '"' + name.replace('"', '""') + '"'


def main():
    if not os.path.isfile(DB_PATH):
        print("ERROR: SQLite database not found:", DB_PATH)
        sys.exit(1)

    try:
        from postgres_adapter import connect_postgres_wrapped
    except Exception as exc:
        print("ERROR: Cannot load PostgreSQL adapter:", type(exc).__name__, str(exc))
        sys.exit(1)

    os.environ["SUPABASE_DB_HOST"] = "aws-1-eu-central-1.pooler.supabase.com"
    os.environ["SUPABASE_DB_PORT"] = "5432"
    os.environ["SUPABASE_DB_NAME"] = "postgres"
    os.environ["SUPABASE_DB_USER"] = "postgres.cmhleervgxnmceyiepba"
    os.environ["SUPABASE_DB_SCHEMA"] = SCHEMA

    password = getpass.getpass("Supabase database password (hidden): ")
    if not password:
        print("ERROR: Password was not provided.")
        sys.exit(1)

    os.environ["SUPABASE_DB_PASSWORD"] = password
    os.environ["DATABASE_PASSWORD"] = password
    os.environ["PGPASSWORD"] = password

    source = None
    destination = None

    try:
        source = sqlite3.connect(DB_PATH)
        source.execute("PRAGMA query_only = ON")

        destination = connect_postgres_wrapped()
        cursor = destination.cursor()

        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """,
            (SCHEMA,),
        )
        pg_tables = {r[0] for r in cursor.fetchall()}

        sqlite_tables = {
            r[0]
            for r in source.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """
            )
        }

        missing = sorted(sqlite_tables - pg_tables)
        extra = sorted(pg_tables - sqlite_tables)

        print("\n=== SUPABASE DATA-INTEGRITY VERIFICATION ===")
        print("Source SQLite tables:", len(sqlite_tables))
        print("Destination Supabase tables:", len(pg_tables))
        print("Missing tables:", missing or "NONE")
        print("Unexpected tables:", extra or "NONE")

        if missing or extra:
            print("RESULT: FAILED — table sets differ.")
            sys.exit(2)

        failures = []
        passed = 0
        total_sqlite = 0
        total_pg = 0

        for table in sorted(sqlite_tables):
            qtable = quote_identifier(table)

            sqlite_info = source.execute(
                "PRAGMA table_info(" + qtable + ")"
            ).fetchall()
            sqlite_columns = [r[1] for r in sqlite_info]

            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema=%s AND table_name=%s
                ORDER BY ordinal_position
                """,
                (SCHEMA, table),
            )
            pg_columns = [r[0] for r in cursor.fetchall()]

            if sqlite_columns != pg_columns:
                failures.append((table, "column order/name mismatch"))
                print("FAIL:", table, "- column order/name mismatch")
                continue

            # Read source rows in SQLite's natural table scan order.
            source_rows = source.execute(
                "SELECT * FROM " + qtable
            ).fetchall()
            source_hashes = sorted(row_digest(tuple(r)) for r in source_rows)

            # Read destination rows. Sorting hashes avoids dependence on
            # database row-return order.
            cursor.execute(
                "SELECT * FROM "
                + quote_identifier(SCHEMA)
                + "."
                + qtable
            )
            destination_rows = cursor.fetchall()
            destination_hashes = sorted(
                row_digest(tuple(r)) for r in destination_rows
            )

            total_sqlite += len(source_rows)
            total_pg += len(destination_rows)

            if len(source_rows) != len(destination_rows):
                failures.append((table, "row count mismatch"))
                print(
                    "FAIL:", table,
                    "| SQLite rows:", len(source_rows),
                    "| Supabase rows:", len(destination_rows)
                )
            elif source_hashes != destination_hashes:
                failures.append((table, "content hash mismatch"))
                print(
                    "FAIL:", table,
                    "| row counts match but content differs"
                )
            else:
                passed += 1
                print(
                    "PASS:", table,
                    "| rows:", len(source_rows),
                    "| contents match"
                )

        print("\n=== SUMMARY ===")
        print("Tables passing content comparison:", passed, "/", len(sqlite_tables))
        print("SQLite rows checked:", total_sqlite)
        print("Supabase rows checked:", total_pg)
        print("Tables with differences:", len(failures))

        if failures:
            print("\nRESULT: DATA VERIFICATION FAILED")
            print("Only table names and failure categories are shown.")
            print("Keep the live application on SQLite.")
            sys.exit(2)

        print("\nRESULT: ALL TABLE CONTENTS MATCH")
        print("This test does not verify data types, defaults, indexes,")
        print("foreign-key enforcement, sequences, or application behavior.")
        print("Keep the live application on SQLite until those checks pass.")

    except Exception as exc:
        print("\nERROR:", type(exc).__name__, str(exc))
        print("No database writes were requested by this script.")
        sys.exit(1)
    finally:
        if source is not None:
            source.close()
        if destination is not None:
            try:
                destination.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
