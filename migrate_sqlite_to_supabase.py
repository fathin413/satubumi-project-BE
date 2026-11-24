"""
Script migrasi data dari SQLite lokal (satubumi.db) ke Supabase PostgreSQL.
Mengkonversi tipe data SQLite (integer 0/1 -> boolean, 'null' -> None, JSON dict -> json.dumps),
menangani orphan foreign key, menjaga ID asli, dan memperbarui sequence auto-increment PostgreSQL.
"""

import os
import json
import sqlite3
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# Daftar kolom bertipe Boolean per tabel di PostgreSQL
BOOLEAN_COLUMNS = {
    "users": ["is_active", "has_rapidfs_access"],
    "alerts": ["is_read", "is_resolved", "auto_generated"],
    "articles": ["is_featured"],
    "team_members": ["is_active"],
    "tree_records": ["is_tag_lost", "is_alive"],
    "tree_measurements": ["is_alive"],
}

# Urutan tabel berdasarkan hierarki relasi Foreign Key
TABLE_ORDER = [
    "users",
    "projects",
    "project_members",
    "team_members",
    "monitoring_plots",
    "tree_records",
    "tree_measurements",
    "carbon_records",
    "biodiversity_observations",
    "community_data",
    "field_reports",
    "landscape_snapshots",
    "project_activities",
    "alerts",
    "assessments",
    "activity_logs",
    "insight_topics",
    "articles",
    "rulebooks",
    "rulebook_downloads",
]


def clean_db_url(url: str) -> str:
    if not url:
        raise ValueError("DATABASE_URL tidak ditemukan di file .env")

    while "??" in url:
        url = url.replace("??", "?")

    url = url.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")

    if "sslmode" not in url:
        separator = "&" if "?" in url else "?"
        url += f"{separator}sslmode=require"

    return url


def clean_row_data(table_name: str, row_dict: dict, valid_user_ids: set) -> dict:
    bool_fields = set(BOOLEAN_COLUMNS.get(table_name, []))

    cleaned = {}
    for k, v in row_dict.items():
        # 1. Konversi boolean SQLite (0/1) ke Boolean Python (False/True)
        if k in bool_fields:
            if v is None:
                cleaned[k] = False
            else:
                cleaned[k] = bool(v)
            continue

        # 2. String 'null' atau 'None' diubah menjadi None (SQL NULL)
        if v == "null" or v == "None":
            cleaned[k] = None
            continue

        # 3. Pastikan dictionary/list di-serialize menjadi JSON string untuk psycopg2
        if isinstance(v, (dict, list)):
            cleaned[k] = json.dumps(v)
            continue

        # 4. Tangani orphan FK di activity_logs (user_id 15 tidak ada di users)
        if table_name == "activity_logs" and k == "user_id":
            if v not in valid_user_ids:
                cleaned[k] = None
                continue

        cleaned[k] = v

    return cleaned


def migrate():
    sqlite_path = "satubumi.db"
    if not os.path.exists(sqlite_path):
        print(f"Error: File database sumber '{sqlite_path}' tidak ditemukan!")
        return

    db_url = clean_db_url(os.getenv("DATABASE_URL"))
    print("Menghubungkan ke Supabase PostgreSQL...")

    try:
        pg_engine = create_engine(db_url)
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Berhasil terhubung ke Supabase!\n")
    except Exception as e:
        print(f"\n[GAGAL KONEKSI KE SUPABASE]: {e}")
        return

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    # Kumpulkan ID user valid untuk cek orphan foreign key
    sqlite_cur.execute("SELECT id FROM users")
    valid_user_ids = set(r[0] for r in sqlite_cur.fetchall())

    total_migrated = 0

    for table in TABLE_ORDER:
        sqlite_cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        if not sqlite_cur.fetchone():
            continue

        sqlite_cur.execute(f'SELECT * FROM "{table}"')
        rows = sqlite_cur.fetchall()
        if not rows:
            continue

        columns = [desc[0] for desc in sqlite_cur.description]
        col_names = ", ".join([f'"{c}"' for c in columns])
        placeholders = ", ".join([f":{c}" for c in columns])

        insert_sql = text(
            f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders}) '
            f'ON CONFLICT DO NOTHING'
        )

        cleaned_data = [
            clean_row_data(table, dict(row), valid_user_ids) for row in rows
        ]

        try:
            with pg_engine.begin() as conn:
                conn.execute(insert_sql, cleaned_data)

                # Update sequence PostgreSQL untuk auto-increment ID
                if "id" in columns:
                    try:
                        seq_sql = text(f"""
                            SELECT setval(
                                pg_get_serial_sequence('{table}', 'id'),
                                COALESCE((SELECT MAX(id) FROM "{table}"), 1),
                                true
                            );
                        """)
                        conn.execute(seq_sql)
                    except Exception:
                        pass

            count = len(cleaned_data)
            total_migrated += count
            print(f"  [OK] Tabel '{table}': {count} baris berhasil dimigrasi.")
        except Exception as ex:
            print(f"  [GAGAL] Tabel '{table}': {ex}")

    sqlite_conn.close()
    print(f"\nSelesai! Total {total_migrated} baris data berhasil di-import ke Supabase!")


if __name__ == "__main__":
    migrate()
