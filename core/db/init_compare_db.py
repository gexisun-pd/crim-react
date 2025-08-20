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
        
        # Create piece_pair_values table
        create_piece_pair_values_table(cursor)
        
        # Create piece_pair_value_sources table
        create_piece_pair_value_sources_table(cursor)
        
        conn.commit()
        print("Melodic ngram values, piece pair values, and piece pair value sources tables initialized successfully")
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

def create_piece_pair_values_table(cursor):
    """
    Create piece_pair_values table to store shared ngram values between piece pairs.
    
    This table stores all shared ngram values between every pair of pieces,
    along with the note_ids for each value in both pieces. It enables efficient
    analysis of musical similarities between pieces.
    """
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS piece_pair_values (
        pair_value_id INTEGER PRIMARY KEY AUTOINCREMENT,
        piece_a_id INTEGER NOT NULL,               -- ID of first piece (piece_a_id <= piece_b_id)
        piece_b_id INTEGER NOT NULL,               -- ID of second piece
        ngram_value TEXT NOT NULL,                 -- The shared ngram pattern
        ngram_length INTEGER NOT NULL,             -- Length of the ngram
        
        -- Note IDs for this value in each piece (JSON arrays)
        notes_in_a TEXT NOT NULL,                  -- JSON array of note_ids in piece A
        notes_in_b TEXT NOT NULL,                  -- JSON array of note_ids in piece B
        
        -- Statistics
        count_in_a INTEGER NOT NULL,               -- Number of occurrences in piece A
        count_in_b INTEGER NOT NULL,               -- Number of occurrences in piece B
        total_shared_notes INTEGER NOT NULL,       -- count_in_a + count_in_b
        
        -- Piece metadata (for faster queries without joins)
        composer_a TEXT NOT NULL,                  -- Composer of piece A
        composer_b TEXT NOT NULL,                  -- Composer of piece B
        same_composer BOOLEAN NOT NULL,            -- Whether pieces are by same composer
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        -- Foreign key constraints
        FOREIGN KEY (piece_a_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
        FOREIGN KEY (piece_b_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
        
        -- Ensure no duplicate pairs and maintain ordering (piece_a_id <= piece_b_id)
        CONSTRAINT unique_piece_pair_value UNIQUE (piece_a_id, piece_b_id, ngram_value),
        CONSTRAINT ordered_pair CHECK (piece_a_id <= piece_b_id)
    );
    
    -- Indexes for efficient querying
    CREATE INDEX IF NOT EXISTS idx_piece_pair_values_piece_a ON piece_pair_values(piece_a_id);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_values_piece_b ON piece_pair_values(piece_b_id);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_values_pair ON piece_pair_values(piece_a_id, piece_b_id);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_values_value ON piece_pair_values(ngram_value);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_values_length ON piece_pair_values(ngram_length);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_values_count_a ON piece_pair_values(count_in_a);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_values_count_b ON piece_pair_values(count_in_b);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_values_total ON piece_pair_values(total_shared_notes);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_values_composer_a ON piece_pair_values(composer_a);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_values_composer_b ON piece_pair_values(composer_b);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_values_same_composer ON piece_pair_values(same_composer);
    """
    
    cursor.executescript(create_table_sql)
    
    # Check if data already exists
    cursor.execute('SELECT COUNT(*) FROM piece_pair_values')
    existing_pairs = cursor.fetchone()[0]
    
    if existing_pairs > 0:
        print(f"Piece pair values table already contains {existing_pairs:,} pair-value records")
    else:
        print("Piece pair values table created (empty)")

def create_piece_pair_value_sources_table(cursor):
    """
    Create piece_pair_value_sources table to store shared ngram values between 
    piece pairs with detailed breakdown by parameter sets.
    
    This table provides a more granular view than piece_pair_values by showing
    exactly which parameter sets contribute to each shared ngram value between pieces.
    """
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS piece_pair_value_sources (
        source_id INTEGER PRIMARY KEY AUTOINCREMENT,
        piece_a_id INTEGER NOT NULL,               -- ID of first piece (piece_a_id <= piece_b_id)
        piece_b_id INTEGER NOT NULL,               -- ID of second piece  
        ngram_value TEXT NOT NULL,                 -- The shared ngram pattern
        set_a_id INTEGER NOT NULL,                 -- Melodic ngram set ID for piece A
        set_b_id INTEGER NOT NULL,                 -- Melodic ngram set ID for piece B
        
        -- Note IDs for this value in each piece from specific sets (JSON arrays)
        notes_in_a TEXT NOT NULL,                  -- JSON array of DISTINCT note_ids from A by set_a
        notes_in_b TEXT NOT NULL,                  -- JSON array of DISTINCT note_ids from B by set_b
        
        -- Statistics
        count_in_a INTEGER NOT NULL,               -- Number of occurrences in piece A from set_a
        count_in_b INTEGER NOT NULL,               -- Number of occurrences in piece B from set_b
        pairs_count INTEGER NOT NULL,              -- count_in_a * count_in_b (potential pairings)
        
        -- Set metadata (for faster queries without joins)
        set_a_slug TEXT NOT NULL,                  -- Slug of set A (e.g., "cT_kq_n3_eF")
        set_b_slug TEXT NOT NULL,                  -- Slug of set B (e.g., "cF_kd_n4_eF")
        same_set_family BOOLEAN NOT NULL,          -- Whether both sets have same base parameters
        
        -- Piece metadata (for faster queries without joins)
        composer_a TEXT NOT NULL,                  -- Composer of piece A
        composer_b TEXT NOT NULL,                  -- Composer of piece B
        same_composer BOOLEAN NOT NULL,            -- Whether pieces are by same composer
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        -- Foreign key constraints
        FOREIGN KEY (piece_a_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
        FOREIGN KEY (piece_b_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
        FOREIGN KEY (set_a_id) REFERENCES melodic_ngram_sets (set_id) ON DELETE CASCADE,
        FOREIGN KEY (set_b_id) REFERENCES melodic_ngram_sets (set_id) ON DELETE CASCADE,
        
        -- Ensure no duplicate records and maintain ordering
        CONSTRAINT unique_piece_pair_value_source UNIQUE (piece_a_id, piece_b_id, ngram_value, set_a_id, set_b_id),
        CONSTRAINT ordered_pair CHECK (piece_a_id <= piece_b_id)
    );
    
    -- Indexes for efficient querying
    CREATE INDEX IF NOT EXISTS idx_piece_pair_value_sources_piece_a ON piece_pair_value_sources(piece_a_id);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_value_sources_piece_b ON piece_pair_value_sources(piece_b_id);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_value_sources_pair ON piece_pair_value_sources(piece_a_id, piece_b_id);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_value_sources_value ON piece_pair_value_sources(ngram_value);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_value_sources_set_a ON piece_pair_value_sources(set_a_id);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_value_sources_set_b ON piece_pair_value_sources(set_b_id);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_value_sources_sets ON piece_pair_value_sources(set_a_id, set_b_id);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_value_sources_pairs_count ON piece_pair_value_sources(pairs_count);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_value_sources_same_set_family ON piece_pair_value_sources(same_set_family);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_value_sources_same_composer ON piece_pair_value_sources(same_composer);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_value_sources_set_a_slug ON piece_pair_value_sources(set_a_slug);
    CREATE INDEX IF NOT EXISTS idx_piece_pair_value_sources_set_b_slug ON piece_pair_value_sources(set_b_slug);
    """
    
    cursor.executescript(create_table_sql)
    
    # Check if data already exists
    cursor.execute('SELECT COUNT(*) FROM piece_pair_value_sources')
    existing_sources = cursor.fetchone()[0]
    
    if existing_sources > 0:
        print(f"Piece pair value sources table already contains {existing_sources:,} source records")
    else:
        print("Piece pair value sources table created (empty)")

def main():
    parser = argparse.ArgumentParser(description='Initialize melodic_ngram_values, piece_pair_values, and piece_pair_value_sources tables')
    
    args = parser.parse_args()
    
    print("=== Melodic Ngram Values and Piece Pair Tables Initialization ===")
    
    # Initialize table
    success = init_compare_database()
    
    if success:
        print("\nTable initialization completed!")
        print("\nNext steps:")
        print("1. Run 'python3 core/compare/melodic_ngram_values.py' to populate the ngram values tables")
        print("2. Run 'python3 core/compare/piece_pair_values.py' to populate the piece pair values table")
        print("3. Run 'python3 core/compare/piece_pair_value_sources.py' to populate the piece pair value sources table")
        print("4. Use the tables for comprehensive piece similarity analysis")
    else:
        print("\nTable initialization failed!")

if __name__ == "__main__":
    main()
