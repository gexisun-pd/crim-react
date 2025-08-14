#!/usr/bin/env python3
"""
Script to update the database schema to include voice_name field
"""

import sys
import os
import sqlite3

# Add the core directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

def update_database_schema():
    """Update the database schema to add voice_name column"""
    
    # Get database path
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'analysis.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if voice_name column already exists in notes table
        cursor.execute("PRAGMA table_info(notes)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'voice_name' not in column_names:
            print("Adding voice_name column to notes table...")
            cursor.execute("ALTER TABLE notes ADD COLUMN voice_name TEXT")
            print("✓ Added voice_name column to notes table")
        else:
            print("✓ voice_name column already exists in notes table")
        
        # Check if voice_name column already exists in melodic_intervals table
        cursor.execute("PRAGMA table_info(melodic_intervals)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'voice_name' not in column_names:
            print("Adding voice_name column to melodic_intervals table...")
            cursor.execute("ALTER TABLE melodic_intervals ADD COLUMN voice_name TEXT")
            print("✓ Added voice_name column to melodic_intervals table")
        else:
            print("✓ voice_name column already exists in melodic_intervals table")
        
        conn.commit()
        conn.close()
        
        print("\n✓ Database schema update completed successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"Error updating database schema: {e}")
        if conn:
            conn.close()
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        if conn:
            conn.close()
        return False

if __name__ == "__main__":
    print("Updating database schema to include voice_name field...")
    success = update_database_schema()
    if success:
        print("\nDatabase schema has been updated successfully!")
        print("You can now run the ingestion scripts with voice name support.")
    else:
        print("\nFailed to update database schema.")
        sys.exit(1)
