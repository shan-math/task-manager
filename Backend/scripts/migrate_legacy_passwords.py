"""
Migrate users from legacy plain `password` column to `password_hash`.
Run once after applying sql/migrate_legacy.sql and new schema.

Usage: python scripts/migrate_legacy_passwords.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()


def main():
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "todo_db"),
    )
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, password FROM users WHERE password IS NOT NULL LIMIT 1")
    except mysql.connector.Error:
        print("No legacy password column; nothing to migrate.")
        return
    cursor.execute("SELECT id, password FROM users WHERE password IS NOT NULL")
    rows = cursor.fetchall()
    for row in rows:
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s AND password_hash IS NULL",
            (generate_password_hash(row["password"]), row["id"]),
        )
    conn.commit()
    print(f"Migrated {len(rows)} user password(s).")
    print("After verifying logins, run: ALTER TABLE users DROP COLUMN password;")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
