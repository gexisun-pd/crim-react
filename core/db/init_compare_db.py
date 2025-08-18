#!/usr/bin/env python3
"""
Initialize database tables for the compare phase of the project.

This script creates the melodic_ngram_values table which serves as an 
inverted index for melodic_ngrams table, organizing note_ids by ngram values.
"""

import sqlite3
import os
import sys
import argparse

# Add the project root to the path to import config
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from core.config import CONFIG

def init_compare_database():
    """Initialize the database with compare-phase tables"""
    db_path = os.path.join(project_root, 'database', 'analysis.db')
    
    if not os.path.exists(db_path):
        print(f"Main database not found at {db_path}")
        print("Please run init_db.py first to create the main database")
        return False
    
    print(f"Initializing melodic_ngram_values table in database: {db_path}")
    
    # Create connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create melodic_ngram_values table
        create_melodic_ngram_values_table(cursor)
        
        conn.commit()
        print("Melodic ngram values table initialized successfully")
        return True
        
    except Exception as e:
        print(f"Error initializing compare database: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def create_melodic_ngram_values_table(cursor):
    """
    Create melodic_ngram_values and related tables as an inverted index for melodic_ngrams.
    
    melodic_ngram_values: Global aggregation of each unique ngram value across all sets
    melodic_ngram_value_sets: Detailed breakdown by set for each ngram value
    """
    
    create_table_sql = """
    -- Main table for global ngram value aggregation
    CREATE TABLE IF NOT EXISTS melodic_ngram_values (
        value_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ngram_value TEXT NOT NULL UNIQUE,           -- The ngram pattern (e.g., "('-2', '-2', '-2')")
        ngram_length INTEGER NOT NULL,              -- Length of the ngram (3, 4, 5, etc.)
        
        -- Global aggregation across all sets
        total_occurrences INTEGER NOT NULL,         -- Total occurrences across all sets
        total_sets INTEGER NOT NULL,               -- Number of sets containing this ngram
        note_ids TEXT NOT NULL,                    -- JSON array of ALL note_ids with this ngram
        
        -- Global piece and composer statistics
        piece_ids TEXT NOT NULL,                   -- JSON array of unique piece_ids
        composers TEXT NOT NULL,                   -- JSON array of unique composers
        piece_count INTEGER NOT NULL,              -- Number of unique pieces
        composer_count INTEGER NOT NULL,           -- Number of unique composers
        
        -- Global voice statistics  
        voice_numbers TEXT NOT NULL,               -- JSON array of voice numbers
        voice_names TEXT NOT NULL,                 -- JSON array of voice names
        voice_count INTEGER NOT NULL,              -- Number of unique voices
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Detailed breakdown by set for each ngram value
    CREATE TABLE IF NOT EXISTS melodic_ngram_value_sets (
        value_set_id INTEGER PRIMARY KEY AUTOINCREMENT,
        value_id INTEGER NOT NULL,                 -- Reference to melodic_ngram_values
        melodic_ngram_set_id INTEGER NOT NULL,     -- Reference to melodic_ngram_sets
        
        -- Set-specific statistics
        set_occurrences INTEGER NOT NULL,          -- Occurrences in this specific set
        set_note_ids TEXT NOT NULL,               -- JSON array of note_ids in this set
        
        -- Set-specific piece and composer statistics
        set_piece_ids TEXT NOT NULL,              -- JSON array of piece_ids in this set
        set_composers TEXT NOT NULL,              -- JSON array of composers in this set
        set_piece_count INTEGER NOT NULL,         -- Number of pieces in this set
        set_composer_count INTEGER NOT NULL,      -- Number of composers in this set
        
        -- Set-specific voice statistics
        set_voice_numbers TEXT NOT NULL,          -- JSON array of voice numbers in this set
        set_voice_names TEXT NOT NULL,            -- JSON array of voice names in this set
        set_voice_count INTEGER NOT NULL,         -- Number of voices in this set
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (value_id) REFERENCES melodic_ngram_values (value_id) ON DELETE CASCADE,
        FOREIGN KEY (melodic_ngram_set_id) REFERENCES melodic_ngram_sets (set_id) ON DELETE CASCADE,
        
        -- Ensure unique combination of value_id and set_id
        UNIQUE(value_id, melodic_ngram_set_id)
    );
    
    -- Indexes for melodic_ngram_values
    CREATE INDEX IF NOT EXISTS idx_melodic_ngram_values_ngram ON melodic_ngram_values(ngram_value);
    CREATE INDEX IF NOT EXISTS idx_melodic_ngram_values_length ON melodic_ngram_values(ngram_length);
    CREATE INDEX IF NOT EXISTS idx_melodic_ngram_values_occurrences ON melodic_ngram_values(total_occurrences);
    CREATE INDEX IF NOT EXISTS idx_melodic_ngram_values_sets ON melodic_ngram_values(total_sets);
    CREATE INDEX IF NOT EXISTS idx_melodic_ngram_values_piece_count ON melodic_ngram_values(piece_count);
    CREATE INDEX IF NOT EXISTS idx_melodic_ngram_values_composer_count ON melodic_ngram_values(composer_count);
    
    -- Indexes for melodic_ngram_value_sets
    CREATE INDEX IF NOT EXISTS idx_melodic_ngram_value_sets_value ON melodic_ngram_value_sets(value_id);
    CREATE INDEX IF NOT EXISTS idx_melodic_ngram_value_sets_set ON melodic_ngram_value_sets(melodic_ngram_set_id);
    CREATE INDEX IF NOT EXISTS idx_melodic_ngram_value_sets_occurrences ON melodic_ngram_value_sets(set_occurrences);
    CREATE INDEX IF NOT EXISTS idx_melodic_ngram_value_sets_pieces ON melodic_ngram_value_sets(set_piece_count);
    """
    
    cursor.executescript(create_table_sql)
    
    # Check if data already exists
    cursor.execute('SELECT COUNT(*) FROM melodic_ngram_values')
    existing_values = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM melodic_ngram_value_sets')
    existing_sets = cursor.fetchone()[0]
    
    if existing_values > 0 or existing_sets > 0:
        print(f"Tables already contain data: {existing_values:,} values, {existing_sets:,} value-set pairs")
    else:
        print("Melodic ngram values tables created (empty)")

def main():
    parser = argparse.ArgumentParser(description='Initialize melodic_ngram_values table')
    
    args = parser.parse_args()
    
    print("=== Melodic Ngram Values Table Initialization ===")
    
    # Initialize table
    success = init_compare_database()
    
    if success:
        print("\nMelodic ngram values table initialization completed!")
        print("\nNext steps:")
        print("1. Run 'python3 core/compare/melodic_ngram_values.py' to populate the table")
        print("2. Use the table for efficient ngram pattern searches")
    else:
        print("\nMelodic ngram values table initialization failed!")

if __name__ == "__main__":
    main()
