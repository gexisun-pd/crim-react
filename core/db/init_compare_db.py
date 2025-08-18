#!/usr/bin/env python3
"""
Initialize database tables for the compare phase of the project.

This script creates the note_pairs table and other tables needed for 
musical analysis comparisons. The note_pairs table contains all possible
pairs of notes from the notes table for comparison analysis.
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
    
    print(f"Initializing compare tables in database: {db_path}")
    
    # Create connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create compare-phase tables
        create_note_pairs_table(cursor)
        create_comparison_results_table(cursor)
        create_similarity_metrics_table(cursor)
        
        conn.commit()
        print("Compare database tables initialized successfully")
        return True
        
    except Exception as e:
        print(f"Error initializing compare database: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def create_note_pairs_table(cursor):
    """
    Create note_pairs table for storing all combinations of note pairs.
    
    This table stores every possible pair of notes from the notes table.
    Each pair (note_a, note_b) represents a potential comparison, where
    note_a and note_b can be from the same piece or different pieces.
    
    Note: (note_a, note_b) and (note_b, note_a) are considered the same pair,
    so we only store pairs where note_a_id <= note_b_id to avoid duplicates.
    """
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS note_pairs (
        note_pair_id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_a_id INTEGER NOT NULL,
        note_b_id INTEGER NOT NULL,
        
        -- Composer information
        composer_a TEXT NOT NULL,
        composer_b TEXT NOT NULL,
        same_composer BOOLEAN NOT NULL,
        
        -- Piece information
        piece_a_id INTEGER NOT NULL,
        piece_b_id INTEGER NOT NULL,
        same_piece BOOLEAN NOT NULL,
        
        -- Voice information
        voice_a INTEGER NOT NULL,
        voice_b INTEGER NOT NULL,
        same_voice BOOLEAN NOT NULL,
        
        -- Timing information
        onset_a REAL NOT NULL,
        onset_b REAL NOT NULL,
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        -- Foreign key constraints
        FOREIGN KEY (note_a_id) REFERENCES notes (note_id) ON DELETE CASCADE,
        FOREIGN KEY (note_b_id) REFERENCES notes (note_id) ON DELETE CASCADE,
        FOREIGN KEY (piece_a_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
        FOREIGN KEY (piece_b_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
        
        -- Ensure no duplicate pairs (note_a_id should be <= note_b_id)
        CONSTRAINT unique_note_pair UNIQUE (note_a_id, note_b_id),
        CONSTRAINT ordered_pair CHECK (note_a_id <= note_b_id)
    );
    
    -- Indexes for efficient querying
    CREATE INDEX IF NOT EXISTS idx_note_pairs_note_a ON note_pairs(note_a_id);
    CREATE INDEX IF NOT EXISTS idx_note_pairs_note_b ON note_pairs(note_b_id);
    CREATE INDEX IF NOT EXISTS idx_note_pairs_composer_a ON note_pairs(composer_a);
    CREATE INDEX IF NOT EXISTS idx_note_pairs_composer_b ON note_pairs(composer_b);
    CREATE INDEX IF NOT EXISTS idx_note_pairs_same_composer ON note_pairs(same_composer);
    CREATE INDEX IF NOT EXISTS idx_note_pairs_piece_a ON note_pairs(piece_a_id);
    CREATE INDEX IF NOT EXISTS idx_note_pairs_piece_b ON note_pairs(piece_b_id);
    CREATE INDEX IF NOT EXISTS idx_note_pairs_same_piece ON note_pairs(same_piece);
    CREATE INDEX IF NOT EXISTS idx_note_pairs_voice_a ON note_pairs(voice_a);
    CREATE INDEX IF NOT EXISTS idx_note_pairs_voice_b ON note_pairs(voice_b);
    CREATE INDEX IF NOT EXISTS idx_note_pairs_same_voice ON note_pairs(same_voice);
    CREATE INDEX IF NOT EXISTS idx_note_pairs_onset_a ON note_pairs(onset_a);
    CREATE INDEX IF NOT EXISTS idx_note_pairs_onset_b ON note_pairs(onset_b);
    """
    
    cursor.executescript(create_table_sql)
    
    # Check if data already exists
    cursor.execute('SELECT COUNT(*) FROM note_pairs')
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"Note pairs table already contains {existing_count:,} pairs")
    else:
        print("Note pairs table created (empty)")

def create_comparison_results_table(cursor):
    """Create table to store comparison results between note pairs"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS comparison_results (
        comparison_id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_pair_id INTEGER NOT NULL,
        
        -- Comparison metadata
        comparison_type TEXT NOT NULL,  -- 'melodic_interval', 'harmonic', 'rhythmic', etc.
        comparison_method TEXT NOT NULL,  -- Algorithm/method used
        
        -- Results
        similarity_score REAL,  -- 0.0 to 1.0, higher = more similar
        distance_score REAL,    -- Distance metric, lower = more similar
        is_match BOOLEAN,       -- Boolean result for exact matches
        confidence REAL,        -- Confidence in the result (0.0 to 1.0)
        
        -- Additional analysis data (JSON format)
        analysis_data TEXT,     -- JSON string with detailed analysis
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (note_pair_id) REFERENCES note_pairs (note_pair_id) ON DELETE CASCADE,
        
        -- Ensure unique comparison per pair and method
        UNIQUE(note_pair_id, comparison_type, comparison_method)
    );
    
    CREATE INDEX IF NOT EXISTS idx_comparison_results_pair ON comparison_results(note_pair_id);
    CREATE INDEX IF NOT EXISTS idx_comparison_results_type ON comparison_results(comparison_type);
    CREATE INDEX IF NOT EXISTS idx_comparison_results_method ON comparison_results(comparison_method);
    CREATE INDEX IF NOT EXISTS idx_comparison_results_similarity ON comparison_results(similarity_score);
    CREATE INDEX IF NOT EXISTS idx_comparison_results_match ON comparison_results(is_match);
    """
    
    cursor.executescript(create_table_sql)
    print("Comparison results table created")

def create_similarity_metrics_table(cursor):
    """Create table to store various similarity metrics and thresholds"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS similarity_metrics (
        metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
        metric_name TEXT NOT NULL UNIQUE,
        metric_type TEXT NOT NULL,  -- 'distance', 'similarity', 'boolean'
        description TEXT,
        
        -- Threshold values for classification
        exact_match_threshold REAL,     -- Threshold for exact matches
        high_similarity_threshold REAL, -- Threshold for high similarity
        moderate_similarity_threshold REAL, -- Threshold for moderate similarity
        
        -- Metric properties
        min_value REAL,  -- Minimum possible value
        max_value REAL,  -- Maximum possible value
        higher_is_better BOOLEAN,  -- True if higher values mean more similar
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_similarity_metrics_name ON similarity_metrics(metric_name);
    CREATE INDEX IF NOT EXISTS idx_similarity_metrics_type ON similarity_metrics(metric_type);
    """
    
    cursor.executescript(create_table_sql)
    print("Similarity metrics table created")

def main():
    parser = argparse.ArgumentParser(description='Initialize compare database tables')
    
    args = parser.parse_args()
    
    print("=== Compare Database Initialization ===")
    
    # Initialize tables
    success = init_compare_database()
    
    if success:
        print("\nCompare database initialization completed!")
        print("\nNext steps:")
        print("1. Run 'python3 core/compare/note_pairs.py' to generate note pairs")
        print("2. Implement comparison algorithms")
        print("3. Run comparison analysis")
    else:
        print("\nCompare database initialization failed!")

if __name__ == "__main__":
    main()
