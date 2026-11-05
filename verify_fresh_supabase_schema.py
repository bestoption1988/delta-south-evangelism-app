import os
import sqlite3
import getpass
import sys

TARGET_SCHEMA = "mcn_migration_fresh_20261018"
SQLITE_DB = os.path.join("data", "evangelism.db")

def main():
    if not os.path.isfile(SQLITE_DB):
        print("ERROR: SQLite database not found:", SQLITE_DB)
        sys.exit(1)

    try:
        from postgres_adapter import connect_postgres_wrapped
    except Exception as exc:
        print("ERROR: Could not load PostgreSQL adapter:", exc)
        sys.exit(1)

    print("Fresh Supabase schema verification")
    print("Target schema:", TARGET_SCHEMA)
    print("Source database:", SQLITE_DB)
    print("This check is read-only.")

    # Configure the existing Supabase Session Pooler connection.
    os.environ["SUPABASE_DB_HOST"] = "aws-1-eu-central-1.pooler.supabase.com"
    os.environ["SUPABASE_DB_PORT"] = "5432"
    os.environ["SUPABASE_DB_NAME"] = "postgres"
    os.environ["SUPABASE_DB_USER"] = "postgres.cmhleervgxnmceyiepba"
    os.environ["SUPABASE_DB_SCHEMA"] = TARGET_SCHEMA

    password = getpass.getpass("Enter Supabase database password (hidden): ")
    if not password:
        print("ERROR: No password entered.")
        sys.exit(1)

    os.environ["SUPABASE_DB_PASSWORD"] = password

    source = None
    destination = None

    try:
        source = sqlite3.connect(SQLITE_DB)
        source.row_factory = sqlite3.Row

        # The adapter may use a different password environment variable.
        # Set common names without printing the secret.
        os.environ["DATABASE_PASSWORD"] = password
        os.environ["PGPASSWORD"] = password

        destination = connect_postgres_wrapped()
        cursor = destination.cursor()

        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """,
            (TARGET_SCHEMA,),
        )
        pg_tables = {row[0] for row in cursor.fetchall()}

        sqlite_tables = {
            row[0]
            for row in source.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
        }

        missing_tables = sorted(sqlite_tables - pg_tables)
        extra_tables = sorted(pg_tables - sqlite_tables)

        print("\nSQLite application tables:", len(sqlite_tables))
        print("Supabase target tables:", len(pg_tables))
        print("Missing tables:", missing_tables or "NONE")
        print("Extra tables:", extra_tables or "NONE")

        column_errors = []
        for table in sorted(sqlite_tables & pg_tables):
            sqlite_columns = [
                row[1]
                for row in source.execute(
                    'PRAGMA table_info("' + table.replace('"', '""') + '")'
                ).fetchall()
            ]

            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                (TARGET_SCHEMA, table),
            )
            pg_columns = [row[0] for row in cursor.fetchall()]

            missing = sorted(set(sqlite_columns) - set(pg_columns))
            extra = sorted(set(pg_columns) - set(sqlite_columns))

            if missing or extra:
                column_errors.append(
                    (table, missing, extra)
                )

        print("\nColumn-name differences:")
        if column_errors:
            for table, missing, extra in column_errors:
                print(
                    " -", table,
                    "| missing in Supabase:", missing,
                    "| extra in Supabase:", extra
                )
        else:
            print("NONE")

        if missing_tables or extra_tables or column_errors:
            print("\nRESULT: SCHEMA VERIFICATION FAILED")
            print("Do not switch the live application to PostgreSQL.")
            sys.exit(2)

        print("\nRESULT: TABLE AND COLUMN NAMES MATCH")
        print("Important: This does not yet verify row contents,")
        print("data types, defaults, indexes, foreign keys, or sequences.")
        print("Keep the live application on SQLite for now.")

    except Exception as exc:
        print("\nERROR during verification:", type(exc).__name__, str(exc))
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
