#!/data/data/com.termux/files/usr/bin/bash

set -u
cd /storage/emulated/0/Download/Delta_South_Evangelism_App_ResponsiveTest || exit 1

REPORT="data/backups/final_postgres_checks_$(date +%Y%m%d_%H%M%S).log"
mkdir -p data/backups

exec > >(tee "$REPORT") 2>&1

FAIL=0

run() {
    echo
    echo "=================================================="
    echo "TEST: $1"
    echo "=================================================="
    shift

    if "$@"; then
        echo "RESULT: PASS"
    else
        echo "RESULT: FAIL"
        FAIL=$((FAIL + 1))
    fi
}

echo "MCN DELTA SOUTH EVANGELISM APP"
echo "FINAL PRE-CUTOVER CHECKS"
echo "Production remains on SQLite."
echo "No production cutover or backup deletion will occur."

run "Python syntax" python -m py_compile \
    app.py database_mode.py database_connection.py \
    postgres_adapter.py postgres_schema_compat.py \
    test_postgres_routes.py verify_postgres_sequences.py

run "PostgreSQL compatibility tests" \
    python test_postgres_compatibility.py

run "Fresh schema verification" \
    python verify_fresh_supabase_schema.py

run "Data integrity verification" \
    python verify_supabase_data_integrity.py

run "Constraint inventory" \
    python verify_supabase_constraints.py

run "Sequence inspection" \
    python verify_postgres_sequences.py

run "Application preflight" \
    python postgres_app_preflight.py

echo
echo "=================================================="
echo "FINAL SUMMARY"
echo "Failed test groups: $FAIL"
echo "Report saved to: $REPORT"
echo "Live production database mode was not changed."
echo "=================================================="

if [ "$FAIL" -eq 0 ]; then
    echo "ALL INCLUDED CHECKS PASSED."
    echo "This is NOT authorization for production cutover."
else
    echo "ONE OR MORE CHECKS FAILED."
    echo "Do not switch production to PostgreSQL."
fi

exit "$FAIL"
