import getpass
import pg8000.dbapi

HOST = "aws-1-eu-central-1.pooler.supabase.com"
PORT = 5432
DATABASE = "postgres"
USER = "postgres.cmhleervgxnmceyiepba"

password = getpass.getpass("Enter your Supabase database password (hidden): ")

try:
    conn = pg8000.dbapi.connect(
        host=HOST,
        port=PORT,
        database=DATABASE,
        user=USER,
        password=password,
        timeout=15,
        ssl_context=True,
    )
    cursor = conn.cursor()
    cursor.execute("SELECT current_database(), current_user, version()")
    row = cursor.fetchone()

    print("\nSUCCESS: Supabase PostgreSQL connection established.")
    print("Database:", row[0])
    print("Connected user:", row[1])
    print("PostgreSQL:", row[2].split(",")[0])

    cursor.close()
    conn.close()

except Exception as exc:
    print("\nCONNECTION FAILED.")
    print("Error type:", type(exc).__name__)
    print("Check your password, network, and Session Pooler settings.")
