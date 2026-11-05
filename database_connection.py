"""Database connection factory for staged backend integration."""

from database_mode import get_database_mode


def connect_database(sqlite_path=None):
    """Connect to the configured backend without initializing its schema."""
    mode = get_database_mode()

    if mode == "sqlite":
        import sqlite3

        if not sqlite_path:
            raise ValueError(
                "sqlite_path is required when SQLite mode is selected."
            )

        connection = sqlite3.connect(sqlite_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    from postgres_adapter import connect_postgres_wrapped

    return connect_postgres_wrapped()


def database_backend():
    """Return the currently selected backend name."""
    return get_database_mode()
