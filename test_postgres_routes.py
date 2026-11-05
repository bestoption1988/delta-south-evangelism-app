import os
import getpass
import sys
import traceback

os.environ["APP_DATABASE_MODE"] = "postgres"
os.environ["SUPABASE_DB_HOST"] = "aws-1-eu-central-1.pooler.supabase.com"
os.environ["SUPABASE_DB_PORT"] = "5432"
os.environ["SUPABASE_DB_NAME"] = "postgres"
os.environ["SUPABASE_DB_USER"] = "postgres.cmhleervgxnmceyiepba"
os.environ["SUPABASE_DB_SCHEMA"] = "mcn_migration_fresh_20261018"
os.environ["SUPABASE_DB_PASSWORD"] = getpass.getpass(
    "Enter Supabase database password (hidden): "
)

failures = []
passed = []

try:
    print("\nLoading Flask application in PostgreSQL mode...")
    import app as application

    flask_app = application.app

    if application.database_backend() != "postgres":
        raise RuntimeError("Application did not select PostgreSQL.")

    print("PASS: Flask application loaded in PostgreSQL mode")

    # Only GET requests are tested here. No registration, payment,
    # financial write, or account-creation endpoints are submitted.
    test_routes = [
        "/",
        "/login",
        "/giving",
        "/live",
        "/api/connection",
        "/api/public/churches",
        "/api/circuits",
        "/api/membership/churches",
    ]

    flask_app.config["TESTING"] = True

    with flask_app.test_client() as client:
        for route in test_routes:
            try:
                response = client.get(route, follow_redirects=False)
                status = response.status_code

                # A redirect or authorization response may be legitimate.
                # Server errors are the main failure signal in this test.
                if status < 500:
                    print(f"PASS: GET {route} -> HTTP {status}")
                    passed.append(route)
                else:
                    print(f"FAIL: GET {route} -> HTTP {status}")
                    failures.append((route, status, None))

            except Exception as exc:
                print(f"FAIL: GET {route} -> {type(exc).__name__}: {exc}")
                failures.append((route, None, str(exc)))

    print("\n========== ROUTE TEST SUMMARY ==========")
    print("Passed:", len(passed))
    print("Failed:", len(failures))

    if failures:
        for route, status, error in failures:
            print("FAILURE:", route, "HTTP:", status, "Error:", error)
        sys.exit(1)

    print("READ-ONLY ROUTE TESTS PASSED")
    print("No production configuration was changed.")

except Exception:
    traceback.print_exc()
    sys.exit(1)

finally:
    os.environ.pop("SUPABASE_DB_PASSWORD", None)
