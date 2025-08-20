#!/usr/bin/env python3
"""
Script to add offset column to notes table
"""
import sys
import os
import sqlite3

def update_schema_add_offset():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'analysis.db')
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(notes)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        if 'offset' not in column_names:
            print("Adding offset column to notes table...")
            cursor.execute("ALTER TABLE notes ADD COLUMN offset REAL")
            print("✓ Added offset column to notes table")
        else:
            print("✓ offset column already exists in notes table")
        conn.commit()
        conn.close()
        print("\n✓ Database schema update completed!")
        return True
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.close()
        return False
if __name__ == "__main__":
    print("Updating notes table to add offset column...")
    update_schema_add_offset()
