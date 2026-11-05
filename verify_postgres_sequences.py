import os
import getpass
import sys

from postgres_adapter import connect_postgres_wrapped

SCHEMA = "mcn_migration_fresh_20261018"

os.environ.update({
    "SUPABASE_DB_HOST": "aws-1-eu-central-1.pooler.supabase.com",
    "SUPABASE_DB_PORT": "5432",
    "SUPABASE_DB_NAME": "postgres",
    "SUPABASE_DB_USER": "postgres.cmhleervgxnmceyiepba",
    "SUPABASE_DB_SCHEMA": SCHEMA,
    "SUPABASE_DB_PASSWORD": getpass.getpass(
        "Enter Supabase database password (hidden): "
    ),
})

connection = None
failures = []

try:
    connection = connect_postgres_wrapped()

    print("\n===== POSTGRESQL IDENTITY SEQUENCE VERIFICATION =====")
    print("Target schema:", SCHEMA)
    print("Read-only checks; no records will be inserted or changed.")

    tables = connection.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = ?
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """, (SCHEMA,)).fetchall()

    checked = 0
    identity_tables = 0

    for item in tables:
        table = item[0]

        columns = connection.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = ?
              AND table_name = ?
              AND is_identity = 'YES'
            ORDER BY ordinal_position
        """, (SCHEMA, table)).fetchall()

        for item_column in columns:
            column = item_column[0]
            identity_tables += 1

            sequence = connection.execute("""
                SELECT pg_get_serial_sequence(?, ?)
            """, (f"{SCHEMA}.{table}", column)).fetchone()[0]

            if not sequence:
                failures.append(
                    f"{table}.{column}: no associated sequence found"
                )
                print(f"FAIL: {table}.{column}: no associated sequence")
                continue

            max_id = connection.execute(
                f'SELECT MAX("{column}") FROM "{SCHEMA}"."{table}"'
            ).fetchone()[0]

            # Query sequence metadata only; never call nextval or setval.
            sequence_name = sequence.rsplit(".", 1)[-1].strip('"')

            state = connection.execute("""
                SELECT last_value
                FROM pg_catalog.pg_sequences
                WHERE schemaname = ?
                  AND sequencename = ?
            """, (SCHEMA, sequence_name)).fetchone()

            checked += 1

            if state is None or state[0] is None:
                print(
                    f"INFO: {table}.{column}: sequence state is not "
                    "visible through pg_sequences; manual verification "
                    "may be needed."
                )
                continue

            last_value = state[0]

            if max_id is None or last_value >= max_id:
                print(
                    f"PASS: {table}.{column}: "
                    f"highest existing ID={max_id}, "
                    f"sequence last_value={last_value}"
                )
            else:
                failures.append(
                    f"{table}.{column}: sequence value {last_value} "
                    f"is below the highest existing ID {max_id}"
                )
                print(
                    f"FAIL: {table}.{column}: sequence value {last_value} "
                    f"is below highest ID {max_id}"
                )

    print("\n===== SUMMARY =====")
    print("Identity columns found:", identity_tables)
    print("Sequence states inspected:", checked)
    print("Failures detected:", len(failures))

    for failure in failures:
        print("FAILURE:", failure)

    if failures:
        print("\nRESULT: INVESTIGATION REQUIRED")
        sys.exit(1)

    print("\nRESULT: NO SEQUENCE VALUES BELOW EXISTING MAXIMUMS DETECTED")
    print(
        "NOTE: This check cannot inspect is_called or prove the next "
        "generated ID is safe. No sequence was advanced."
    )

finally:
    if connection is not None:
        connection.close()
    os.environ.pop("SUPABASE_DB_PASSWORD", None)
