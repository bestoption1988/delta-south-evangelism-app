"""PostgreSQL equivalents for SQLite schema-inspection helpers."""

from postgres_adapter import validate_identifier


def postgres_table_info(connection, schema, table):
    """Return SQLite-PRAGMA-like column metadata rows.

    Each row supports numeric access:
      row[0] = ordinal/cid
      row[1] = column name
      row[2] = data type
      row[3] = not-null flag
      row[4] = default value
      row[5] = primary-key flag
    """
    schema = validate_identifier(schema)
    table = validate_identifier(table)

    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                CASE WHEN pk.column_name IS NULL THEN 0 ELSE 1 END
            FROM information_schema.columns AS c
            LEFT JOIN (
                SELECT ku.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS ku
                  ON ku.constraint_name = tc.constraint_name
                 AND ku.constraint_schema = tc.constraint_schema
                 AND ku.table_schema = tc.table_schema
                 AND ku.table_name = tc.table_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = %s
                  AND tc.table_name = %s
            ) AS pk ON pk.column_name = c.column_name
            WHERE c.table_schema = %s
              AND c.table_name = %s
            ORDER BY c.ordinal_position
            """,
            (schema, table, schema, table),
        )
        results = cursor.fetchall()

        return [
            (
                index,
                row[0],
                row[1],
                1 if row[2] == "NO" else 0,
                row[3],
                row[4],
            )
            for index, row in enumerate(results)
        ]
    finally:
        cursor.close()


def postgres_list_tables(connection, schema):
    """List ordinary tables in a PostgreSQL schema."""
    schema = validate_identifier(schema)
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """,
            (schema,),
        )
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
