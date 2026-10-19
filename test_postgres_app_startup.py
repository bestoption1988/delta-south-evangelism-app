import os
import getpass
import traceback

os.environ["APP_DATABASE_MODE"] = "postgres"
os.environ["SUPABASE_DB_HOST"] = "aws-1-eu-central-1.pooler.supabase.com"
os.environ["SUPABASE_DB_PORT"] = "5432"
os.environ["SUPABASE_DB_NAME"] = "postgres"
os.environ["SUPABASE_DB_USER"] = "postgres.cmhleervgxnmceyiepba"
os.environ["SUPABASE_DB_SCHEMA"] = "mcn_migration_fresh_20261018"

password = getpass.getpass("Enter Supabase database password (hidden): ")
os.environ["SUPABASE_DB_PASSWORD"] = password

print("\nTesting Flask application startup in PostgreSQL mode...")
print("Target schema:", os.environ["SUPABASE_DB_SCHEMA"])
print("Production configuration will not be changed.")

try:
    import app as application

    backend = application.database_backend()
    print("Application backend:", backend)

    if backend != "postgres":
        raise RuntimeError("Application did not select PostgreSQL.")

    if not hasattr(application, "app"):
        raise RuntimeError("Flask application object was not found.")

    print("Registered Flask application:", type(application.app).__name__)
    print("Application startup: PASS")
    print("No production cutover performed.")

except Exception as exc:
    print("\nAPPLICATION STARTUP: FAILED")
    print("Error type:", type(exc).__name__)
    print("Error:", str(exc))
    traceback.print_exc()
    raise SystemExit(1)
