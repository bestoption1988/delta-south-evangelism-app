import getpass
import pg8000.dbapi

HOST = "aws-1-eu-central-1.pooler.supabase.com"
PORT = 5432
DATABASE = "postgres"
USER = "postgres.cmhleervgxnmceyiepba"

password = getpass.getpass("Supabase database password (hidden): ")

conn = None

try:
    conn = pg8000.dbapi.connect(
        host=HOST,
        port=PORT,
        database=DATABASE,
        user=USER,
        password=password,
        timeout=20,
        ssl_context=True,
    )

    cur = conn.cursor()

    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)

    tables = [row[0] for row in cur.fetchall()]

    print("\nExisting public tables:", len(tables))
    for table in tables:
        print(" -", table)

    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'church_media_library'
        ORDER BY ordinal_position
    """)

    columns = cur.fetchall()

    print("\nChurch media library columns:")
    if columns:
        for name, data_type in columns:
            print(f" - {name}: {data_type}")
    else:
        print(" - Table not found")

    cur.close()

except Exception as exc:
    print("\nInspection failed:", type(exc).__name__, str(exc))

finally:
    if conn:
        conn.close()
