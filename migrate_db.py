"""
Database migration script to add missing columns
Run this script to update existing database schema
"""
import sqlite3
from app import app
from models.product import db

def migrate_database():
    """Add missing columns to existing tables"""
    db_path = 'fit_sports_hub.db'
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Check if updated_at column exists in admins table
        cursor.execute("PRAGMA table_info(admins)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'updated_at' not in columns:
            print("Adding updated_at column to admins table...")
            cursor.execute("""
                ALTER TABLE admins 
                ADD COLUMN updated_at DATETIME
            """)
            # Set default value for existing rows
            cursor.execute("""
                UPDATE admins 
                SET updated_at = created_at 
                WHERE updated_at IS NULL
            """)
            conn.commit()
            print("Migration completed successfully!")
        else:
            print("Column already exists, no migration needed.")

if __name__ == '__main__':
    migrate_database()
