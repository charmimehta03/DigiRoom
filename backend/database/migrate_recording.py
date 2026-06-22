"""
migrate_recording.py
====================
Adds the three new nullable columns to lecture_recordings table.
Safe to run multiple times (checks if columns already exist).

Run once after pulling the recording feature update:
    python migrate_recording.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "digiroom.db")
DB_PATH = os.path.normpath(DB_PATH)


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def run():
    print(f"Connecting to: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    migrations = [
        ("marker_path",      "TEXT"),
        ("file_size",        "INTEGER"),
        ("duration_seconds", "INTEGER"),
    ]

    for col_name, col_type in migrations:
        if column_exists(cur, "lecture_recordings", col_name):
            print(f"  [skip]  lecture_recordings.{col_name} already exists")
        else:
            cur.execute(
                f"ALTER TABLE lecture_recordings ADD COLUMN {col_name} {col_type}"
            )
            print(f"  [added] lecture_recordings.{col_name} {col_type}")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    run()
