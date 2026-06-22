"""
Migration: Poll Correct-Answer + Individual Student Analytics
---------------------------------------------------------------
Adds the following columns to the EXISTING SQLite database
without touching any existing rows or tables:

    lecture_polls.correct_option           (TEXT, nullable)
    lecture_poll_answers.is_correct        (TEXT, nullable)
    lecture_analytics.face_present_count   (INTEGER, default 0)
    lecture_analytics.face_missing_count   (INTEGER, default 0)

Safe to run multiple times (checks PRAGMA table_info before
adding each column, so re-running is a no-op).

Usage:
    python -m backend.database.migrate_poll_analytics
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "digiroom.db")


def _existing_columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def _add_column_if_missing(cursor, table, column, ddl_type):
    cols = _existing_columns(cursor, table)
    if column in cols:
        print(f"  [skip] {table}.{column} already exists")
        return False

    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")
    print(f"  [add ] {table}.{column} {ddl_type}")
    return True


def run_migration(db_path: str = DB_PATH):
    if not os.path.exists(db_path):
        print(f"No database found at {db_path} — nothing to migrate "
              f"(a fresh DB will be created with the new schema already "
              f"included on next app startup).")
        return

    print(f"Migrating database at {db_path} ...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    changed = False

    # --- lecture_polls.correct_option -------------------------------
    changed |= _add_column_if_missing(
        cursor, "lecture_polls", "correct_option", "TEXT"
    )

    # --- lecture_poll_answers.is_correct ------------------------------
    changed |= _add_column_if_missing(
        cursor, "lecture_poll_answers", "is_correct", "TEXT"
    )

    # --- lecture_analytics.face_present_count / face_missing_count ---
    changed |= _add_column_if_missing(
        cursor, "lecture_analytics", "face_present_count", "INTEGER DEFAULT 0"
    )
    changed |= _add_column_if_missing(
        cursor, "lecture_analytics", "face_missing_count", "INTEGER DEFAULT 0"
    )

    conn.commit()
    conn.close()

    if changed:
        print("Migration complete. Existing data preserved; new columns are NULL/0 for old rows.")
    else:
        print("Database already up to date. No changes made.")


if __name__ == "__main__":
    run_migration()
