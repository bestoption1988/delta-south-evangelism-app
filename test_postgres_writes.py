import getpass
import os
from postgres_adapter import connect_postgres_wrapped

os.environ.update({
    "SUPABASE_DB_HOST": "aws-1-eu-central-1.pooler.supabase.com",
    "SUPABASE_DB_PORT": "5432",
    "SUPABASE_DB_NAME": "postgres",
    "SUPABASE_DB_USER": "postgres.cmhleervgxnmceyiepba",
    "SUPABASE_DB_PASSWORD": getpass.getpass("Supabase password (hidden): "),
})

conn = None

try:
    conn = connect_postgres_wrapped()

    conn.execute("""
        CREATE TEMPORARY TABLE adapter_write_test (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            test_name TEXT NOT NULL,
            test_value INTEGER NOT NULL
        )
    """)

    cursor = conn.cursor()
    cursor.execute_insert_returning_id(
        """
        INSERT INTO adapter_write_test (test_name, test_value)
        VALUES (?, ?)
        """,
        ("adapter-check", 10),
    )
    new_id = cursor.lastrowid
    cursor.close()

    print("Generated ID:", new_id)

    row = conn.execute(
        "SELECT test_name, test_value FROM adapter_write_test WHERE id = ?",
        (new_id,),
    ).fetchone()

    assert row["test_name"] == "adapter-check"
    assert row["test_value"] == 10
    print("INSERT PASSED")

    conn.execute(
        "UPDATE adapter_write_test SET test_value = ? WHERE id = ?",
        (20, new_id),
    )

    updated = conn.execute(
        "SELECT test_value FROM adapter_write_test WHERE id = ?",
        (new_id,),
    ).fetchone()

    assert updated["test_value"] == 20
    print("UPDATE PASSED")

    conn.rollback()
    print("ROLLBACK COMPLETED")
    print("WRITE TESTS PASSED")

except Exception as exc:
    if conn:
        conn.rollback()
    print("TEST FAILED:", type(exc).__name__, str(exc)[:250])

finally:
    if conn:
        conn.close()
    os.environ.pop("SUPABASE_DB_PASSWORD", None)
