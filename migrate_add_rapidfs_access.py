import sqlite3

conn = sqlite3.connect("satubumi.db")
cursor = conn.cursor()

try:
    cursor.execute("""
    ALTER TABLE users
    ADD COLUMN has_rapidfs_access BOOLEAN DEFAULT 0
    """)
    conn.commit()
    print("Column has_rapidfs_access added successfully to users table.")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower():
        print("Column has_rapidfs_access already exists.")
    else:
        print(f"Error: {e}")
finally:
    conn.close()
