"""
One-time migration: adds columns needed for the super-admin feature
to an existing certichain.db (db.create_all() only creates missing
TABLES, it never adds missing COLUMNS to tables that already exist).

Safe to re-run — skips any column/table that already exists.
"""
import sqlite3
import os

DB_PATH = os.path.join('instance', 'certichain.db')


def column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def main():
    if not os.path.exists(DB_PATH):
        print(f"Base introuvable : {DB_PATH} — rien à migrer (sera créée au démarrage de l'app).")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if not column_exists(cur, 'institutions', 'is_active'):
        cur.execute("ALTER TABLE institutions ADD COLUMN is_active BOOLEAN DEFAULT 1")
        print("✓ institutions.is_active ajoutée")
    else:
        print("- institutions.is_active déjà présente")

    if not column_exists(cur, 'certificates', 'email_sent_at'):
        cur.execute("ALTER TABLE certificates ADD COLUMN email_sent_at DATETIME")
        print("✓ certificates.email_sent_at ajoutée")
    else:
        print("- certificates.email_sent_at déjà présente")

    conn.commit()
    conn.close()
    print("Migration terminée. La table 'admins' sera créée automatiquement au prochain démarrage de l'app.")


if __name__ == '__main__':
    main()
