import os
import sys
import pg8000.dbapi

required = [
    "SUPABASE_DB_HOST",
    "SUPABASE_DB_PORT",
    "SUPABASE_DB_NAME",
    "SUPABASE_DB_USER",
    "SUPABASE_DB_PASSWORD",
]

missing = [key for key in required if not os.environ.get(key)]

if missing:
    print("Missing environment variables:", ", ".join(missing))
    sys.exit(2)

try:
    conn = pg8000.dbapi.connect(
        host=os.environ["SUPABASE_DB_HOST"],
        port=int(os.environ["SUPABASE_DB_PORT"]),
        database=os.environ["SUPABASE_DB_NAME"],
        user=os.environ["SUPABASE_DB_USER"],
        password=os.environ["SUPABASE_DB_PASSWORD"],
        timeout=15,
        ssl_context=True,
    )
    cur = conn.cursor()
    cur.execute("SELECT current_database(), current_user")
    print("CONNECTED:", cur.fetchone())
    cur.close()
    conn.close()

except Exception as exc:
    print("ERROR TYPE:", type(exc).__name__)

    # PostgreSQL errors can include server messages.
    # Avoid printing connection arguments or credentials.
    msg = str(exc)
    for secret in [
        os.environ.get("SUPABASE_DB_PASSWORD", ""),
    ]:
        if secret:
            msg = msg.replace(secret, "[REDACTED]")

    print("ERROR MESSAGE:", msg[:500])
    sys.exit(1)
