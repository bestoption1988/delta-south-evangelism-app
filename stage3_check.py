import os, sqlite3, getpass
from pathlib import Path
from postgres_adapter import connect_postgres_wrapped

root = Path.cwd()
os.environ.update({
    "SUPABASE_DB_HOST": "aws-1-eu-central-1.pooler.supabase.com",
    "SUPABASE_DB_PORT": "5432",
    "SUPABASE_DB_NAME": "postgres",
    "SUPABASE_DB_USER": "postgres.cmhleervgxnmceyiepba",
    "SUPABASE_DB_PASSWORD": getpass.getpass("Supabase password (hidden): ")
})
conn = None
try:
    conn = connect_postgres_wrapped()
    with sqlite3.connect((root/"data/evangelism.db").resolve().as_uri()+"?mode=ro", uri=True) as db:
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        mismatches = []
        for t in tables:
            src = [r[1] for r in db.execute(f'PRAGMA table_info("{t}")')]
            pg = conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position",
                ("mcn_migration_test", t)
            ).fetchall()
            dst = [r["column_name"] for r in pg]
            if src != dst:
                mismatches.append(t)
        inventory = conn.execute(
            "SELECT count(*) AS n FROM pg_indexes WHERE schemaname=%s",
            ("mcn_migration_test",)
        ).fetchone()["n"]
        print("SQLite tables:", len(tables))
        print("Column mismatches:", mismatches or "None")
        print("PostgreSQL indexes:", inventory)
        print("STAGE 3:", "PASS" if not mismatches else "NEEDS REVIEW")
except Exception as e:
    print("CHECK FAILED:", type(e).__name__, str(e)[:180])
finally:
    if conn:
        try: conn.close()
        except Exception: pass
    os.environ.pop("SUPABASE_DB_PASSWORD", None)
