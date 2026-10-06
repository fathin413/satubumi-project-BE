import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'), override=True)

from sqlalchemy import text
from app.core.database import engine

def migrate():
    print(f'Migrating database (dialect: {engine.dialect.name})...')
    with engine.connect() as conn:
        try:
            if engine.dialect.name == 'sqlite':
                conn.execute(text('ALTER TABLE users ADD COLUMN has_rapidfs_access BOOLEAN DEFAULT 0;'))
            else:
                conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS has_rapidfs_access BOOLEAN DEFAULT FALSE;'))
            conn.commit()
            print('Column has_rapidfs_access successfully ensured in users table.')
        except Exception as e:
            if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                print('Column has_rapidfs_access already exists.')
            else:
                print(f'Migration note/error: {e}')

if __name__ == '__main__':
    migrate()
