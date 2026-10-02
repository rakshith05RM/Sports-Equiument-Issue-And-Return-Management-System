"""
Fieldhouse — one-time setup script.

Run this once after you have created the database using database.sql.
database.sql inserts the 'admin' and 'staff1' user rows with placeholder
password hashes (since SQL cannot compute Werkzeug's hashing algorithm).
This script connects to MySQL and updates those two rows with real,
securely-hashed passwords. Anyone who registers afterwards through the
app's /register page goes through the normal pending-approval flow —
this script only exists to bootstrap the two seed accounts.

Usage:
    python seed_admin.py

Default credentials created:
    Admin -> username: admin   password: Admin@123
    Staff -> username: staff1  password: Staff@123

You should change these passwords after first login in a real deployment.
"""

from werkzeug.security import generate_password_hash
from database import get_db_connection


def main():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            admin_hash = generate_password_hash("Admin@123")
            staff_hash = generate_password_hash("Staff@123")

            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE username = %s",
                (admin_hash, "admin"),
            )
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE username = %s",
                (staff_hash, "staff1"),
            )
        conn.commit()
        print("Default admin/staff passwords have been set successfully.")
        print("Admin login  -> username: admin  | password: Admin@123")
        print("Staff login  -> username: staff1 | password: Staff@123")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
