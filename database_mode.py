"""Explicit database-mode selection for staged PostgreSQL integration."""

import os


def get_database_mode():
    """Return sqlite or postgres; SQLite remains the safe default."""
    mode = os.environ.get("APP_DATABASE_MODE", "sqlite").strip().lower()

    if mode not in ("sqlite", "postgres"):
        raise ValueError(
            "APP_DATABASE_MODE must be either 'sqlite' or 'postgres'."
        )

    return mode


def postgres_mode_enabled():
    return get_database_mode() == "postgres"
