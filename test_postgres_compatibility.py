from postgres_adapter import PostgreSQLCursor, PostgreSQLRow

def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS:", message)

# Test SQLite-style placeholder conversion.
convert = PostgreSQLCursor._convert_placeholders
check(
    convert("SELECT * FROM members WHERE id=? AND name=?")
    == "SELECT * FROM members WHERE id=%s AND name=%s",
    "Question-mark placeholders"
)
check(
    convert("SELECT '?' AS literal, id FROM members WHERE id=?")
    == "SELECT '?' AS literal, id FROM members WHERE id=%s",
    "Question marks inside quoted strings are preserved"
)
check(
    convert('SELECT "?" AS literal, id FROM members WHERE id=?')
    == 'SELECT "?" AS literal, id FROM members WHERE id=%s',
    "Question marks inside quoted identifiers are preserved"
)

# Test dictionary-style and numeric row access.
row = PostgreSQLRow(("id", "full_name"), (7, "Test Member"))
check(row["id"] == 7, "Row access by column name")
check(row[0] == 7, "Row access by numeric index")
check(row.get("missing", "fallback") == "fallback", "Row get fallback")

# Confirm the adapter exposes the explicit generated-ID helper.
check(
    callable(getattr(PostgreSQLCursor, "execute_insert_returning_id", None)),
    "Generated-ID helper exists"
)

print("\nCOMPATIBILITY UNIT TESTS PASSED")
print("No application code or database records changed.")
