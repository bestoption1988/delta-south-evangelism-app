"""
Experimental PostgreSQL adapter for MCN Delta South Evangelism App.

This module is isolated from app.py.
It does not connect to a database until explicitly requested.
It does not modify the live SQLite application.
"""

import os
import re
import pg8000.dbapi


class PostgreSQLAdapterError(RuntimeError):
    """Raised when PostgreSQL adapter configuration is invalid."""


def postgres_config():
    """Read PostgreSQL settings without hardcoding database credentials."""
    required = (
        "SUPABASE_DB_HOST",
        "SUPABASE_DB_PORT",
        "SUPABASE_DB_NAME",
        "SUPABASE_DB_USER",
        "SUPABASE_DB_PASSWORD",
    )

    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise PostgreSQLAdapterError(
            "Missing PostgreSQL environment variables: "
            + ", ".join(missing)
        )

    try:
        port = int(os.environ["SUPABASE_DB_PORT"])
    except ValueError as exc:
        raise PostgreSQLAdapterError(
            "SUPABASE_DB_PORT must be an integer."
        ) from exc

    if not 1 <= port <= 65535:
        raise PostgreSQLAdapterError(
            "SUPABASE_DB_PORT is outside the valid range."
        )

    schema = os.environ.get("SUPABASE_DB_SCHEMA", "public").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema):
        raise PostgreSQLAdapterError(
            "SUPABASE_DB_SCHEMA must be a simple PostgreSQL schema identifier."
        )

    return {
        "host": os.environ["SUPABASE_DB_HOST"],
        "port": port,
        "database": os.environ["SUPABASE_DB_NAME"],
        "user": os.environ["SUPABASE_DB_USER"],
        "password": os.environ["SUPABASE_DB_PASSWORD"],
        "timeout": 15,
        "ssl_context": True,
        "startup_params": {"search_path": schema},
    }


def connect_postgres():
    """Open a PostgreSQL connection when explicitly requested."""
    return pg8000.dbapi.connect(**postgres_config())


def validate_identifier(identifier):
    """Accept simple SQL identifiers only."""
    if not isinstance(identifier, str):
        raise ValueError("SQL identifier must be a string.")

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise ValueError("Invalid SQL identifier.")

    return identifier


def postgres_table_columns(connection, schema, table):
    """Return column names using PostgreSQL metadata."""
    schema = validate_identifier(schema)
    table = validate_identifier(table)

    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, table),
        )
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()


def postgres_table_exists(connection, schema, table):
    """Check whether a table exists in a specific schema."""
    schema = validate_identifier(schema)
    table = validate_identifier(table)

    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_name = %s
                  AND table_type = 'BASE TABLE'
            )
            """,
            (schema, table),
        )
        return bool(cursor.fetchone()[0])
    finally:
        cursor.close()


def postgres_health_check(connection):
    """Check connectivity without changing any database records."""
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT current_database(),
                   current_user,
                   current_schema(),
                   version()
            """
        )
        row = cursor.fetchone()

        return {
            "database": row[0],
            "user": row[1],
            "current_schema": row[2],
            "version": row[3],
        }
    finally:
        cursor.close()


class PostgreSQLRow:
    """Allow row access by both column name and numeric index."""

    def __init__(self, columns, values):
        self._columns = tuple(columns)
        self._values = tuple(values)
        self._index = {
            name: index for index, name in enumerate(self._columns)
        }

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._index[key]]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return self._columns

    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, IndexError, TypeError):
            return default


class PostgreSQLCursor:
    """Cursor wrapper for basic PostgreSQL queries."""

    def __init__(self, cursor):
        self._cursor = cursor
        self._lastrowid = None
        self._pending_row = None

    @property
    def lastrowid(self):
        return self._lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    @staticmethod
    def _convert_placeholders(sql):
        """Convert simple SQLite ? placeholders outside SQL string literals."""
        result = []
        quote = None
        i = 0

        while i < len(sql):
            char = sql[i]

            if quote:
                result.append(char)
                if char == quote:
                    if i + 1 < len(sql) and sql[i + 1] == quote:
                        result.append(sql[i + 1])
                        i += 1
                    else:
                        quote = None
            elif char in ("'", '"'):
                quote = char
                result.append(char)
            elif char == "?":
                result.append("%s")
            else:
                result.append(char)

            i += 1

        return "".join(result)

    @staticmethod
    def _split_sql_statements(script):
        """Split ordinary SQL on semicolons outside quoted strings."""
        statements = []
        start = 0
        quote = None
        i = 0

        while i < len(script):
            char = script[i]

            if quote:
                if char == quote:
                    if i + 1 < len(script) and script[i + 1] == quote:
                        i += 2
                        continue
                    quote = None
            elif char in ("'", '"'):
                quote = char
            elif char == ";":
                statement = script[start:i].strip()
                if statement:
                    statements.append(statement)
                start = i + 1

            i += 1

        if quote:
            raise ValueError("Unterminated quoted string in SQL script.")

        tail = script[start:].strip()
        if tail:
            statements.append(tail)

        return statements

    @staticmethod
    def _translate_sql(sql):
        """Translate a small, explicit subset of SQLite SQL to PostgreSQL."""
        statement = sql.strip()

        # PostgreSQL uses ON CONFLICT DO NOTHING instead of INSERT OR IGNORE.
        match = re.match(r"^INSERT\s+OR\s+IGNORE\s+INTO\b", statement, re.I)
        if match:
            statement = re.sub(
                r"^INSERT\s+OR\s+IGNORE\s+INTO\b",
                "INSERT INTO",
                statement,
                count=1,
                flags=re.I,
            )
            if not re.search(r"\bON\s+CONFLICT\b", statement, re.I):
                statement += " ON CONFLICT DO NOTHING"

        # Do not silently discard SQLite's case-insensitive collation.
        # Call sites must use an explicit PostgreSQL-compatible expression.
        if re.search(r"\bCOLLATE\s+NOCASE\b", statement, re.I):
            raise NotImplementedError(
                "COLLATE NOCASE requires an explicit case-insensitive SQL translation."
            )

        # Do not silently pass SQLite-only AUTOINCREMENT syntax to PostgreSQL.
        if re.search(r"\bAUTOINCREMENT\b", statement, re.I):
            raise NotImplementedError(
                "SQLite AUTOINCREMENT needs an explicit PostgreSQL schema migration."
            )

        return statement

    def executescript(self, script):
        """Execute simple SQL statements individually; caller manages commit."""
        for statement in self._split_sql_statements(script):
            self.execute(self._translate_sql(statement))
        return self

    def execute(self, sql, args=None):
        sql = self._translate_sql(sql)
        params = () if args is None else args
        statement = sql.strip().rstrip(";")
        self._lastrowid = None
        self._pending_row = None

        # Preserve caller-managed RETURNING queries.
        match = re.match(
            r'^INSERT\s+INTO\s+'
            r'(?:(?:"?([A-Za-z_][A-Za-z0-9_]*)"?)[.])?'
            r'"?([A-Za-z_][A-Za-z0-9_]*)"?\b',
            statement,
            re.IGNORECASE,
        )

        if match and not re.search(r'\bRETURNING\b', statement, re.IGNORECASE):
            target_schema, target_table = match.groups()
            relation_name = (
                f"{target_schema}.{target_table}"
                if target_schema
                else target_table
            )

            self._cursor.execute(
                """
                SELECT a.attidentity
                FROM pg_catalog.pg_attribute AS a
                WHERE a.attrelid = pg_catalog.to_regclass(%s)
                  AND a.attname = 'id'
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                """,
                (relation_name,),
            )
            metadata = self._cursor.fetchone()
            has_identity_id = metadata is not None and metadata[0] in ("a", "d")

            if has_identity_id:
                self._cursor.execute(
                    self._convert_placeholders(statement + " RETURNING id"),
                    params,
                )
                row = self._cursor.fetchone()
                self._lastrowid = row[0] if row else None
                return self

        self._cursor.execute(
            self._convert_placeholders(statement),
            params,
        )
        return self

    def execute_insert_returning_id(self, sql, args=None):
        statement = sql.strip().rstrip(";")
        if not statement.upper().startswith("INSERT INTO "):
            raise ValueError("Expected an INSERT INTO statement.")
        if " RETURNING " not in statement.upper():
            statement += " RETURNING id"

        self._cursor.execute(
            self._convert_placeholders(statement),
            () if args is None else args,
        )
        row = self._cursor.fetchone()
        self._lastrowid = row[0] if row else None
        return self

    def fetchone(self):
        if self._pending_row is not None:
            row = self._pending_row
            self._pending_row = None
            return row

        row = self._cursor.fetchone()
        if row is None:
            return None

        columns = [item[0] for item in self._cursor.description]
        return PostgreSQLRow(columns, row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []

        columns = [item[0] for item in self._cursor.description]
        return [PostgreSQLRow(columns, row) for row in rows]

    def close(self):
        self._cursor.close()


class PostgreSQLConnection:
    """Connection wrapper for testing ordinary PostgreSQL queries."""

    def __init__(self, connection):
        self._connection = connection

    def execute(self, sql, args=None):
        cursor = PostgreSQLCursor(self._connection.cursor())
        return cursor.execute(sql, args)

    def cursor(self):
        return PostgreSQLCursor(self._connection.cursor())

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()


def connect_postgres_wrapped():
    """Connect and return the basic compatibility wrapper."""
    return PostgreSQLConnection(connect_postgres())
