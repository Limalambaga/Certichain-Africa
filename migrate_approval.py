"""
One-time migration: adds the is_approved column needed for the
institution-approval gate. Existing institutions are auto-approved
(they were already trusted/in-use before this feature existed) —
only NEW signups going forward default to is_approved=False.

Works against the local SQLite DB by default. To run against the
production Postgres DB, set DATABASE_URL before running this script.

Safe to re-run.
"""
import os
import sys


def migrate_sqlite():
    import sqlite3
    db_path = os.path.join('instance', 'certichain.db')
    if not os.path.exists(db_path):
        print(f"SQLite DB not found at {db_path} — nothing to migrate.")
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(institutions)")
    cols = [r[1] for r in cur.fetchall()]
    if 'is_approved' not in cols:
        cur.execute("ALTER TABLE institutions ADD COLUMN is_approved BOOLEAN DEFAULT 0")
        print("- institutions.is_approved column added")
    else:
        print("- institutions.is_approved already exists")
    cur.execute("UPDATE institutions SET is_approved = 1 WHERE is_approved IS NULL OR is_approved = 0")
    conn.commit()
    print(f"- {cur.rowcount} existing institution(s) auto-approved")
    conn.close()


def migrate_postgres(database_url):
    import psycopg2
    conn = psycopg2.connect(database_url, connect_timeout=10)
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'institutions' AND column_name = 'is_approved'
    """)
    if not cur.fetchone():
        cur.execute("ALTER TABLE institutions ADD COLUMN is_approved BOOLEAN DEFAULT FALSE")
        print("- institutions.is_approved column added (Postgres)")
    else:
        print("- institutions.is_approved already exists (Postgres)")
    cur.execute("UPDATE institutions SET is_approved = TRUE WHERE is_approved IS NULL OR is_approved = FALSE")
    print(f"- {cur.rowcount} existing institution(s) auto-approved (Postgres)")
    conn.commit()
    conn.close()


if __name__ == '__main__':
    db_url = os.getenv('DATABASE_URL') or (sys.argv[1] if len(sys.argv) > 1 else None)
    if db_url:
        migrate_postgres(db_url)
    else:
        migrate_sqlite()
    print("Migration complete.")
