import os
import sys
import json
import sqlite3
import getpass

DB_PATH = "data/evangelism.db"
SCHEMA = "mcn_migration_fresh_20261018"


def qi(name):
    return '"' + name.replace('"', '""') + '"'


def main():
    if not os.path.isfile(DB_PATH):
        print("ERROR: SQLite database not found:", DB_PATH)
        sys.exit(1)

    try:
        from postgres_adapter import connect_postgres_wrapped
    except Exception as exc:
        print("ERROR: Cannot load PostgreSQL adapter:", exc)
        sys.exit(1)

    os.environ["SUPABASE_DB_HOST"] = "aws-1-eu-central-1.pooler.supabase.com"
    os.environ["SUPABASE_DB_PORT"] = "5432"
    os.environ["SUPABASE_DB_NAME"] = "postgres"
    os.environ["SUPABASE_DB_USER"] = "postgres.cmhleervgxnmceyiepba"
    os.environ["SUPABASE_DB_SCHEMA"] = SCHEMA

    password = getpass.getpass("Supabase database password (hidden): ")
    if not password:
        print("ERROR: No password entered.")
        sys.exit(1)

    os.environ["SUPABASE_DB_PASSWORD"] = password
    os.environ["DATABASE_PASSWORD"] = password
    os.environ["PGPASSWORD"] = password

    source = None
    destination = None

    try:
        source = sqlite3.connect(DB_PATH)
        source.execute("PRAGMA query_only=ON")
        destination = connect_postgres_wrapped()
        cursor = destination.cursor()

        print("\n===== SUPABASE CONSTRAINT VERIFICATION =====")
        print("Destination schema:", SCHEMA)
        print("Read-only checks only.")

        # Compare primary-key columns.
        pk_errors = []
        for table_row in source.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """):
            table = table_row[0]
            info = source.execute(
                "PRAGMA table_info(" + qi(table) + ")"
            ).fetchall()
            sqlite_pk = [
                (r[5], r[1]) for r in info if r[5] > 0
            ]
            sqlite_pk.sort()

            cursor.execute("""
                SELECT kcu.ordinal_position, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_catalog = kcu.constraint_catalog
                 AND tc.constraint_schema = kcu.constraint_schema
                 AND tc.constraint_name = kcu.constraint_name
                 AND tc.table_name = kcu.table_name
                WHERE tc.constraint_schema=%s
                  AND tc.table_name=%s
                  AND tc.constraint_type='PRIMARY KEY'
                ORDER BY kcu.ordinal_position
            """, (SCHEMA, table))
            pg_pk = [(r[0], r[1]) for r in cursor.fetchall()]

            # SQLite PK ordinal positions are the PRAGMA pk values.
            if [name for _, name in sqlite_pk] != [
                name for _, name in pg_pk
            ]:
                pk_errors.append(table)
                print(
                    "PRIMARY KEY DIFFERENCE:", table,
                    "| SQLite:", [n for _, n in sqlite_pk],
                    "| Supabase:", [n for _, n in pg_pk]
                )

        if not pk_errors:
            print("PASS: Primary-key columns match for all tables.")

        # Report unique constraints and indexes in both databases.
        sqlite_unique = {}
        for table_row in source.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """):
            table = table_row[0]
            entries = []
            for idx in source.execute(
                "PRAGMA index_list(" + qi(table) + ")"
            ).fetchall():
                if idx[2]:
                    idx_name = idx[1]
                    cols = source.execute(
                        "PRAGMA index_info(" + qi(idx_name) + ")"
                    ).fetchall()
                    entries.append({
                        "name": idx_name,
                        "columns": [r[2] for r in cols],
                        "partial": bool(idx[4]) if len(idx) > 4 else False
                    })
            sqlite_unique[table] = entries

        cursor.execute("""
            SELECT tc.table_name, tc.constraint_name,
                   kcu.column_name, kcu.ordinal_position
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_catalog = kcu.constraint_catalog
             AND tc.constraint_schema = kcu.constraint_schema
             AND tc.constraint_name = kcu.constraint_name
             AND tc.table_name = kcu.table_name
            WHERE tc.constraint_schema=%s
              AND tc.constraint_type='UNIQUE'
            ORDER BY tc.table_name, tc.constraint_name,
                     kcu.ordinal_position
        """, (SCHEMA,))
        unique_constraints = cursor.fetchall()

        cursor.execute("""
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname=%s
            ORDER BY tablename, indexname
        """, (SCHEMA,))
        pg_indexes = cursor.fetchall()

        print("\nSQLite tables with unique indexes:",
              sum(bool(v) for v in sqlite_unique.values()))
        print("Supabase unique constraints:", len(unique_constraints))
        print("Supabase indexes:", len(pg_indexes))

        # Check every declared SQLite foreign key is represented in PostgreSQL.
        expected_fks = []
        for table_row in source.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """):
            table = table_row[0]
            for fk in source.execute(
                "PRAGMA foreign_key_list(" + qi(table) + ")"
            ).fetchall():
                expected_fks.append((
                    table, fk[2], fk[3], fk[4]
                ))

        cursor.execute("""
            SELECT tc.table_name, ccu.table_name,
                   kcu.column_name, ccu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_catalog = kcu.constraint_catalog
             AND tc.constraint_schema = kcu.constraint_schema
             AND tc.constraint_name = kcu.constraint_name
             AND tc.table_name = kcu.table_name
            JOIN information_schema.constraint_column_usage ccu
              ON tc.constraint_catalog = ccu.constraint_catalog
             AND tc.constraint_schema = ccu.constraint_schema
             AND tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_schema=%s
              AND tc.constraint_type='FOREIGN KEY'
            ORDER BY tc.table_name, ccu.table_name,
                     kcu.column_name, ccu.column_name
        """, (SCHEMA,))
        actual_fks = set(tuple(r) for r in cursor.fetchall())

        missing_fks = sorted(set(expected_fks) - actual_fks)
        extra_fks = sorted(actual_fks - set(expected_fks))

        print("\nSQLite declared foreign keys:", len(expected_fks))
        print("Supabase declared foreign keys:", len(actual_fks))
        print("Missing foreign keys:", missing_fks or "NONE")
        print("Additional foreign keys:", extra_fks or "NONE")

        # Check that PostgreSQL currently has no violations of its own
        # declared foreign keys. This does not prove all SQLite FKs exist.
        cursor.execute("""
            SELECT tc.table_name, tc.constraint_name
            FROM information_schema.table_constraints tc
            WHERE tc.constraint_schema=%s
              AND tc.constraint_type='FOREIGN KEY'
            ORDER BY tc.table_name, tc.constraint_name
        """, (SCHEMA,))
        pg_fk_constraints = cursor.fetchall()

        print("\nForeign-key constraint definitions inspected:",
              len(pg_fk_constraints))
        print("Note: this script does not alter constraints or records.")

        if pk_errors or missing_fks or extra_fks:
            print("\nRESULT: REVIEW REQUIRED")
            print("Keep the live application on SQLite.")
            sys.exit(2)

        print("\nRESULT: PRIMARY KEYS AND DECLARED FOREIGN KEYS MATCH")
        print("Unique indexes and constraints were inventoried.")
        print("Their full semantic equivalence still needs review.")
        print("Sequence behavior, column types/defaults and app behavior")
        print("must be checked before production cutover.")
        print("Keep the live application on SQLite.")

    except Exception as exc:
        print("\nERROR:", type(exc).__name__, str(exc))
        print("No database writes were requested.")
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
