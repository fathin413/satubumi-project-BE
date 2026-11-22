"""
Migrate script: Add tree census fields to tree_records table in SQLite / PostgreSQL.
Fields:
- local_name (VARCHAR(255))
- circumference_cm (FLOAT DEFAULT 0.0)
- is_tag_lost (BOOLEAN DEFAULT FALSE)
- created_by (INTEGER)
- created_by_name (VARCHAR(255))
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text
from app.core.database import engine


def migrate():
    print("Memulai migrasi untuk tabel tree_records...")
    inspector = inspect(engine)
    existing_columns = {col["name"] for col in inspector.get_columns("tree_records")}

    columns_to_add = [
        ("local_name", "VARCHAR(255)"),
        ("circumference_cm", "FLOAT DEFAULT 0.0"),
        ("is_tag_lost", "BOOLEAN DEFAULT FALSE"),
        ("created_by", "INTEGER"),
        ("created_by_name", "VARCHAR(255)"),
    ]

    with engine.connect() as conn:
        for col_name, col_type in columns_to_add:
            if col_name in existing_columns:
                print(f"Kolom {col_name} sudah ada, dilewati.")
                continue

            try:
                conn.execute(text(f"ALTER TABLE tree_records ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Berhasil menambahkan kolom {col_name} ({col_type})")
            except Exception as e:
                print(f"Catatan kolom {col_name}: {e}")

    print("Migrasi selesai dengan sukses!")


if __name__ == "__main__":
    migrate()
