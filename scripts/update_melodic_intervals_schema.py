#!/usr/bin/env python3
"""
Script to update the melodic_intervals table schema to include note_id references.
This will drop the existing table and recreate it with the new structure.
"""

import os
import sys
import sqlite3

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def update_melodic_intervals_schema():
    """Update the melodic_intervals table schema"""
    
    # Get database path
    project_root = os.path.dirname(os.path.dirname(__file__))
    db_path = os.path.join(project_root, 'database', 'analysis.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("Please run the database initialization script first.")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if melodic_intervals table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='melodic_intervals'
        """)
        
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            print("Dropping existing melodic_intervals table...")
            cursor.execute("DROP TABLE melodic_intervals")
        
        print("Creating new melodic_intervals table with note_id references...")
        
        # Create new table with updated schema
        create_table_sql = """
        CREATE TABLE melodic_intervals (
            interval_id INTEGER PRIMARY KEY AUTOINCREMENT,
            piece_id INTEGER NOT NULL,
            note_id INTEGER,                 -- 关联到notes表的note_id (起始音符)
            next_note_id INTEGER,            -- 关联到notes表的note_id (结束音符)
            voice INTEGER NOT NULL,
            onset REAL NOT NULL,             -- 音程开始时间
            measure INTEGER,
            beat REAL,
            interval_semitones REAL,         -- 音程的半音数
            interval_type TEXT,              -- 音程类型描述 (如 "major 3rd")
            interval_direction TEXT,         -- 音程方向: "ascending", "descending", "unison"
            interval_quality TEXT,           -- 音程性质
            voice_name TEXT,                 -- 声部名称
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (piece_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
            FOREIGN KEY (note_id) REFERENCES notes (note_id) ON DELETE SET NULL,
            FOREIGN KEY (next_note_id) REFERENCES notes (note_id) ON DELETE SET NULL
        );
        """
        
        cursor.execute(create_table_sql)
        
        # Create indexes
        indexes_sql = [
            "CREATE INDEX idx_melodic_intervals_piece ON melodic_intervals(piece_id);",
            "CREATE INDEX idx_melodic_intervals_voice ON melodic_intervals(voice);",
            "CREATE INDEX idx_melodic_intervals_onset ON melodic_intervals(onset);",
            "CREATE INDEX idx_melodic_intervals_note ON melodic_intervals(note_id);",
            "CREATE INDEX idx_melodic_intervals_next_note ON melodic_intervals(next_note_id);"
        ]
        
        for index_sql in indexes_sql:
            cursor.execute(index_sql)
        
        conn.commit()
        conn.close()
        
        print("✅ Successfully updated melodic_intervals table schema")
        print("📋 New table includes:")
        print("   - note_id: References the starting note of the interval")
        print("   - next_note_id: References the ending note of the interval")
        print("   - Proper foreign key constraints")
        print("   - Optimized indexes for queries")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating schema: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("🔄 Updating melodic_intervals table schema...")
    success = update_melodic_intervals_schema()
    
    if success:
        print("\n✨ Schema update completed successfully!")
        print("📌 You can now run ingest_melodic_intervals.py to populate the table.")
    else:
        print("\n❌ Schema update failed!")
        sys.exit(1)
