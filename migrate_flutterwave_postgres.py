import sys

from database_connection import connect_database
from database_mode import get_database_mode

REQUIRED = {
    "income": {
        "id", "date", "donor_name", "source", "fund", "amount",
        "method", "reference", "received_by", "notes",
        "member_id", "church_account_id"
    },
    "payment_transactions": {
        "id", "reference", "gateway", "status", "amount", "currency",
        "purpose", "account_level", "circuit", "church_name",
        "church_account_id", "member_id", "donor_name", "donor_email",
        "donor_phone", "payment_method", "gateway_transaction_id",
        "gateway_response", "paid_at", "created_at"
    },
    "audit_log": {
        "id", "happened_at", "action", "table_name", "record_id",
        "details", "user_id", "username"
    }
}

INDEX_NAME = "ux_income_reference_nonempty"


def main():
    apply_changes = "--apply" in sys.argv

    if get_database_mode() != "postgres":
        raise RuntimeError(
            "Migration refused: APP_DATABASE_MODE must be postgres."
        )

    conn = connect_database()

    try:
        target = conn.execute("""
            SELECT current_database(), current_user, current_schema()
        """).fetchone()

        database_name, database_user, schema_name = target

        print("\n===== POSTGRESQL TARGET =====")
        print("Database:", database_name)
        print("Database user:", database_user)
        print("Schema:", schema_name)

        if not database_name or not schema_name:
            raise RuntimeError("Could not identify PostgreSQL target.")

        for table, required in REQUIRED.items():
            rows = conn.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = ?
            """, (table,)).fetchall()

            actual = {row[0] for row in rows}

            print("\n===== TABLE:", table, "=====")

            if not actual:
                raise RuntimeError("Required table is missing: " + table)

            missing = required - actual

            if missing:
                raise RuntimeError(
                    "Missing columns in " + table + ": "
                    + ", ".join(sorted(missing))
                )

            print("All required columns exist.")

        print("\n===== DUPLICATE INCOME REFERENCES =====")

        duplicates = conn.execute("""
            SELECT reference, COUNT(*)
            FROM income
            WHERE reference IS NOT NULL
              AND TRIM(reference) <> ''
            GROUP BY reference
            HAVING COUNT(*) > 1
            LIMIT 20
        """).fetchall()

        if duplicates:
            print("STOP: Duplicate references detected.")
            for row in duplicates:
                print("Reference:", row[0], "Count:", row[1])
            raise RuntimeError("Resolve duplicates before migration.")

        print("No duplicate non-empty references.")

        print("\n===== EXISTING INDEX CHECK =====")

        index = conn.execute("""
            SELECT indexdef
            FROM pg_indexes
            WHERE schemaname = current_schema()
              AND tablename = 'income'
              AND indexname = ?
        """, (INDEX_NAME,)).fetchone()

        if index:
            definition = str(index[0])
            print("Existing index:", definition)

            # Do not guess whether PostgreSQL's formatted index
            # definition is equivalent. Display it for manual review.
            print("Existing index requires definition review.")
            print("No index changes will be made automatically.")
            return

        print("Required unique partial index is absent.")

        if not apply_changes:
            print("\nPREVIEW ONLY. No database changes were made.")
            print("After reviewing the production diagnostic,")
            print("the migration can be applied with --apply.")
            return

        print("\nApplying unique income reference index...")

        conn.execute("""
            CREATE UNIQUE INDEX ux_income_reference_nonempty
            ON income(reference)
            WHERE reference IS NOT NULL
              AND TRIM(reference) <> ''
        """)

        conn.commit()
        print("SUCCESS: Unique income reference index created.")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
