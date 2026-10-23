#!/usr/bin/env python3
"""Additive MCN Delta South Fellowship Management schema migration.

This script creates only new fellowship_* tables and seeds four profiles.
It does not modify or delete existing tables. Back up the database first.

SQLite:
  APP_DATABASE_MODE=sqlite python migrate_fellowship_management.py

PostgreSQL/Supabase:
  APP_DATABASE_MODE=postgres DATABASE_URL='postgresql://...' python migrate_fellowship_management.py
"""
import argparse
import os
import sqlite3
import sys
from urllib.parse import urlparse, unquote

FELLOWSHIPS = [
    ("methodist-mens-fellowship", "Methodist Men’s Fellowship", "men"),
    ("methodist-womens-fellowship", "Methodist Women’s Fellowship", "women"),
    ("methodist-youth-fellowship", "Methodist Youth Fellowship", "youth"),
    ("methodist-campus-fellowship", "Methodist Campus Fellowship (MCF)", "campus"),
]

TABLE_COLUMNS = {
    "fellowship_chapters": """id {pk}, fellowship_id BIGINT NOT NULL REFERENCES fellowships(id) ON DELETE CASCADE,
      chapter_type TEXT NOT NULL DEFAULT 'church', chapter_name TEXT NOT NULL,
      circuit TEXT NOT NULL DEFAULT '', church_name TEXT NOT NULL DEFAULT '',
      campus_name TEXT NOT NULL DEFAULT '', location TEXT NOT NULL DEFAULT '',
      contact_name TEXT NOT NULL DEFAULT '', contact_phone TEXT NOT NULL DEFAULT '',
      active INTEGER NOT NULL DEFAULT 1, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, created_by BIGINT,
      UNIQUE(fellowship_id, chapter_type, chapter_name, circuit, church_name, campus_name)""",
    "fellowship_leaders": """id {pk}, fellowship_id BIGINT NOT NULL REFERENCES fellowships(id) ON DELETE CASCADE,
      chapter_id BIGINT REFERENCES fellowship_chapters(id) ON DELETE SET NULL,
      full_name TEXT NOT NULL, position_title TEXT NOT NULL, biography TEXT NOT NULL DEFAULT '',
      photo_path TEXT NOT NULL DEFAULT '', term_start TEXT NOT NULL DEFAULT '', term_end TEXT NOT NULL DEFAULT '',
      display_order INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
      scope_type TEXT NOT NULL DEFAULT 'diocese', scope_value TEXT NOT NULL DEFAULT '',
      circuit TEXT NOT NULL DEFAULT '', church_name TEXT NOT NULL DEFAULT '',
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      created_by BIGINT, updated_by BIGINT""",
    "fellowship_announcements": """id {pk}, fellowship_id BIGINT NOT NULL REFERENCES fellowships(id) ON DELETE CASCADE,
      chapter_id BIGINT REFERENCES fellowship_chapters(id) ON DELETE SET NULL, title TEXT NOT NULL,
      body TEXT NOT NULL DEFAULT '', image_path TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'draft',
      scope_type TEXT NOT NULL DEFAULT 'diocese', scope_value TEXT NOT NULL DEFAULT '',
      circuit TEXT NOT NULL DEFAULT '', church_name TEXT NOT NULL DEFAULT '', published_at TIMESTAMP,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      created_by BIGINT, updated_by BIGINT""",
    "fellowship_events": """id {pk}, fellowship_id BIGINT NOT NULL REFERENCES fellowships(id) ON DELETE CASCADE,
      chapter_id BIGINT REFERENCES fellowship_chapters(id) ON DELETE SET NULL, title TEXT NOT NULL,
      description TEXT NOT NULL DEFAULT '', event_type TEXT NOT NULL DEFAULT 'programme', venue TEXT NOT NULL DEFAULT '',
      starts_at TEXT NOT NULL DEFAULT '', ends_at TEXT NOT NULL DEFAULT '', poster_path TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'draft', scope_type TEXT NOT NULL DEFAULT 'diocese', scope_value TEXT NOT NULL DEFAULT '',
      circuit TEXT NOT NULL DEFAULT '', church_name TEXT NOT NULL DEFAULT '', published_at TIMESTAMP,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      created_by BIGINT, updated_by BIGINT""",
    "fellowship_studies": """id {pk}, fellowship_id BIGINT NOT NULL REFERENCES fellowships(id) ON DELETE CASCADE,
      chapter_id BIGINT REFERENCES fellowship_chapters(id) ON DELETE SET NULL,
      content_type TEXT NOT NULL DEFAULT 'bible_study', title TEXT NOT NULL,
      scripture_reference TEXT NOT NULL DEFAULT '', preacher_or_teacher TEXT NOT NULL DEFAULT '',
      summary TEXT NOT NULL DEFAULT '', content TEXT NOT NULL DEFAULT '', media_path TEXT NOT NULL DEFAULT '',
      event_date TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'draft',
      scope_type TEXT NOT NULL DEFAULT 'diocese', scope_value TEXT NOT NULL DEFAULT '',
      circuit TEXT NOT NULL DEFAULT '', church_name TEXT NOT NULL DEFAULT '', published_at TIMESTAMP,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      created_by BIGINT, updated_by BIGINT""",
    "fellowship_members": """id {pk}, fellowship_id BIGINT NOT NULL REFERENCES fellowships(id) ON DELETE CASCADE,
      member_id BIGINT NOT NULL REFERENCES members(id) ON DELETE CASCADE,
      chapter_id BIGINT REFERENCES fellowship_chapters(id) ON DELETE SET NULL,
      membership_role TEXT NOT NULL DEFAULT 'member', joined_on TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'active', notes TEXT NOT NULL DEFAULT '',
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      created_by BIGINT, UNIQUE(fellowship_id, member_id)""",
    "fellowship_gallery": """id {pk}, fellowship_id BIGINT NOT NULL REFERENCES fellowships(id) ON DELETE CASCADE,
      chapter_id BIGINT REFERENCES fellowship_chapters(id) ON DELETE SET NULL,
      title TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '', media_path TEXT NOT NULL,
      media_type TEXT NOT NULL DEFAULT 'image', event_date TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'draft', scope_type TEXT NOT NULL DEFAULT 'diocese',
      scope_value TEXT NOT NULL DEFAULT '', circuit TEXT NOT NULL DEFAULT '', church_name TEXT NOT NULL DEFAULT '',
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      created_by BIGINT, updated_by BIGINT""",
    "fellowship_reports": """id {pk}, fellowship_id BIGINT NOT NULL REFERENCES fellowships(id) ON DELETE CASCADE,
      chapter_id BIGINT REFERENCES fellowship_chapters(id) ON DELETE SET NULL, title TEXT NOT NULL,
      report_period TEXT NOT NULL DEFAULT '', summary TEXT NOT NULL DEFAULT '', report_path TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'draft', scope_type TEXT NOT NULL DEFAULT 'diocese',
      scope_value TEXT NOT NULL DEFAULT '', circuit TEXT NOT NULL DEFAULT '', church_name TEXT NOT NULL DEFAULT '',
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      created_by BIGINT, updated_by BIGINT""",
}

def sqlite_migrate(path):
    if not os.path.isfile(path):
        raise RuntimeError(f"SQLite database not found: {path}. No database was created.")
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "members" not in existing:
            raise RuntimeError("Existing members table not found; refusing to migrate the wrong database.")
        conn.execute("""CREATE TABLE IF NOT EXISTS fellowships (
          id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
          short_name TEXT NOT NULL, logo_path TEXT NOT NULL DEFAULT '', cover_path TEXT NOT NULL DEFAULT '',
          introduction TEXT NOT NULL DEFAULT '', history TEXT NOT NULL DEFAULT '', vision TEXT NOT NULL DEFAULT '',
          mission TEXT NOT NULL DEFAULT '', objectives TEXT NOT NULL DEFAULT '',
          scope_type TEXT NOT NULL DEFAULT 'diocese', scope_value TEXT NOT NULL DEFAULT '',
          circuit TEXT NOT NULL DEFAULT '', church_name TEXT NOT NULL DEFAULT '', chapter_name TEXT NOT NULL DEFAULT '',
          active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, created_by INTEGER, updated_by INTEGER)""")
        for table, columns in TABLE_COLUMNS.items():
            ddl = columns.format(pk="INTEGER PRIMARY KEY AUTOINCREMENT").replace("TIMESTAMP", "TEXT")
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({ddl})")
        for slug, name, short in FELLOWSHIPS:
            conn.execute("INSERT OR IGNORE INTO fellowships(slug,name,short_name) VALUES(?,?,?)", (slug,name,short))
        conn.commit()
        return conn.execute("SELECT COUNT(*) FROM fellowships").fetchone()[0]
    finally:
        conn.close()

def postgres_migrate(url, yes):
    import re

    try:
        import pg8000.dbapi
    except ImportError as e:
        raise RuntimeError(
            "Install pg8000 in the app environment first: pip install pg8000"
        ) from e

    parsed = urlparse(url)
    if parsed.scheme not in ("postgres", "postgresql"):
        raise RuntimeError("DATABASE_URL must be a PostgreSQL URL.")

    schema = os.environ.get(
        "POSTGRES_DB_SCHEMA",
        os.environ.get("SUPABASE_DB_SCHEMA", "public"),
    ).strip()

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema):
        raise RuntimeError("Invalid PostgreSQL schema identifier.")

    if not parsed.hostname or not parsed.path.strip("/"):
        raise RuntimeError("DATABASE_URL must include a host and database name.")

    if not parsed.username or not parsed.password:
        raise RuntimeError("DATABASE_URL must include a username and password.")

    if not yes:
        print("This adds fellowship tables to the configured PostgreSQL schema.")
        print("Target schema:", schema)
        print("Existing membership tables and records will not be intentionally altered.")
        if input("Type APPLY FELLOWSHIP MIGRATION to continue: ").strip() != \
                "APPLY FELLOWSHIP MIGRATION":
            print("Cancelled; no changes applied.")
            return

    conn = pg8000.dbapi.connect(
        user=unquote(parsed.username),
        password=unquote(parsed.password),
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=unquote(parsed.path.strip("/")),
        ssl_context=True,
        startup_params={"search_path": schema},
    )

    try:
        cur = conn.cursor()

        # Confirm the selected schema and existing member table.
        cur.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
            (schema,),
        )
        if cur.fetchone() is None:
            raise RuntimeError(
                f"Configured schema {schema!r} does not exist; refusing to migrate."
            )

        cur.execute(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = 'members'
              AND column_name = 'id'
            """,
            (schema,),
        )
        member_id = cur.fetchone()
        if member_id is None:
            raise RuntimeError(
                f"{schema}.members.id not found; refusing to migrate."
            )

        # Existing member IDs must be BIGINT-compatible for the FK.
        if member_id[0] not in ("bigint", "integer", "smallint"):
            raise RuntimeError(
                f"Unexpected {schema}.members.id type: {member_id[0]}; "
                "review foreign-key compatibility before migrating."
            )

        cur.execute("""
            CREATE TABLE IF NOT EXISTS fellowships (
              id BIGSERIAL PRIMARY KEY,
              slug TEXT NOT NULL UNIQUE,
              name TEXT NOT NULL,
              short_name TEXT NOT NULL,
              logo_path TEXT NOT NULL DEFAULT '',
              cover_path TEXT NOT NULL DEFAULT '',
              introduction TEXT NOT NULL DEFAULT '',
              history TEXT NOT NULL DEFAULT '',
              vision TEXT NOT NULL DEFAULT '',
              mission TEXT NOT NULL DEFAULT '',
              objectives TEXT NOT NULL DEFAULT '',
              scope_type TEXT NOT NULL DEFAULT 'diocese',
              scope_value TEXT NOT NULL DEFAULT '',
              circuit TEXT NOT NULL DEFAULT '',
              church_name TEXT NOT NULL DEFAULT '',
              chapter_name TEXT NOT NULL DEFAULT '',
              active INTEGER NOT NULL DEFAULT 1,
              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              created_by BIGINT,
              updated_by BIGINT
            )
        """)

        for table, columns in TABLE_COLUMNS.items():
            ddl = columns.format(pk="BIGSERIAL PRIMARY KEY")
            cur.execute(f"CREATE TABLE IF NOT EXISTS {table} ({ddl})")

        for slug, name, short in FELLOWSHIPS:
            cur.execute(
                """
                INSERT INTO fellowships(slug, name, short_name)
                VALUES (%s, %s, %s)
                ON CONFLICT(slug) DO NOTHING
                """,
                (slug, name, short),
            )

        conn.commit()
        cur.execute("SELECT COUNT(*) FROM fellowships")
        print(
            f"SUCCESS: schema {schema!r} is ready. "
            "Fellowship profiles:", cur.fetchone()[0]
        )
        cur.close()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--yes", action="store_true", help="skip PostgreSQL confirmation")
    p.add_argument("--sqlite-path", default=os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "evangelism.db")))
    a = p.parse_args()
    mode = os.environ.get("APP_DATABASE_MODE", "sqlite").lower().strip()
    if mode in ("sqlite", "sqlite3", ""):
        count = sqlite_migrate(os.path.abspath(a.sqlite_path))
        print("SUCCESS: SQLite fellowship schema is ready. Seeded profiles:", count)
        print("No existing tables were altered or deleted.")
    elif mode in ("postgres", "postgresql", "pg"):
        url = os.environ.get("DATABASE_URL", "").strip()
        if not url:
            sys.exit("STOP: DATABASE_URL is not set.")
        postgres_migrate(url, a.yes)
    else:
        sys.exit("Unsupported APP_DATABASE_MODE: " + mode)

if __name__ == "__main__":
    main()
