#!/usr/bin/env python3
"""
Script to clear all notes data from the database.
This will delete all records from the notes table while keeping the pieces table intact.
"""

import os
import sys
import sqlite3

def clear_notes_table():
    """Clear all notes from the database"""
    
    # Get project root directory (one level up from scripts/)
    project_root = os.path.dirname(os.path.dirname(__file__))
    db_path = os.path.join(project_root, 'database', 'analysis.db')
    
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM notes")
        count_before = cursor.fetchone()[0]
        
        if count_before == 0:
            print("Notes table is already empty.")
            conn.close()
            return True
        
        print(f"Found {count_before} notes in the database.")
        
        # Ask for confirmation
        response = input(f"Are you sure you want to delete all {count_before} notes? (yes/no): ")
        
        if response.lower() not in ['yes', 'y']:
            print("Operation cancelled.")
            conn.close()
            return False
        
        # Delete all notes
        cursor.execute("DELETE FROM notes")
        
        # Get count after deletion to verify
        cursor.execute("SELECT COUNT(*) FROM notes")
        count_after = cursor.fetchone()[0]
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print(f"Successfully deleted {count_before} notes from the database.")
        print(f"Notes table now contains {count_after} records.")
        
        # Reset auto-increment counter (optional)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='notes'")
        conn.commit()
        conn.close()
        
        print("Auto-increment counter has been reset.")
        
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.close()
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        if conn:
            conn.close()
        return False

def main():
    """Main function"""
    print("=== Clear Notes Table ===")
    print("This script will delete ALL notes from the database.")
    print("The pieces table will remain unchanged.")
    print()
    
    success = clear_notes_table()
    
    if success:
        print("\nNotes table cleared successfully!")
        print("You can now run ingest_notes.py to re-populate the notes.")
    else:
        print("\nFailed to clear notes table.")
        sys.exit(1)

if __name__ == "__main__":
    main()
