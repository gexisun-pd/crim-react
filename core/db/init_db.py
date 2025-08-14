import sqlite3
import os
import sys
import itertools

# Add the project root to the path to import config
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from core.config import CONFIG

def init_database():
    """Initialize the database with schema.sql and parameter sets"""
    # Get the project root directory (two levels up from core/db/)
    db_path = os.path.join(project_root, 'database', 'analysis.db')
    schema_path = os.path.join(project_root, 'database', 'schema.sql')
    
    # Remove existing database to ensure clean state
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database at {db_path}")
    
    # Create connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Read and execute schema
    with open(schema_path, 'r') as f:
        schema = f.read()
        cursor.executescript(schema)
    
    # Generate and insert note_sets (combination of notes_combine_unisons)
    create_note_sets(cursor)
    
    # Generate and insert melodic_interval_sets (combination of melodic_intervals_kind and melodic_ngrams_number)
    create_melodic_interval_sets(cursor)
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {db_path}")

def create_note_sets(cursor):
    """Create note_sets table with all combinations of notes_combine_unisons"""
    # Create note_sets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS note_sets (
            set_id INTEGER PRIMARY KEY AUTOINCREMENT,
            combine_unisons BOOLEAN NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(combine_unisons)
        )
    ''')
    
    # Clear existing data
    cursor.execute('DELETE FROM note_sets')
    
    # Insert all combinations
    for combine_unisons in CONFIG['notes_combine_unisons']:
        slug = "cT" if combine_unisons else "cF"
        description = f"combine_unisons_{combine_unisons}"
        cursor.execute('''
            INSERT INTO note_sets (combine_unisons, slug, description)
            VALUES (?, ?, ?)
        ''', (combine_unisons, slug, description))
    
    count = cursor.rowcount
    print(f"Created {count} note sets")

def create_melodic_interval_sets(cursor):
    """Create melodic_interval_sets table with all combinations of kind and note_sets"""
    # Drop and recreate melodic_interval_sets table
    cursor.execute('DROP TABLE IF EXISTS melodic_interval_sets')
    cursor.execute('''
        CREATE TABLE melodic_interval_sets (
            set_id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            note_set_id INTEGER NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(kind, note_set_id),
            FOREIGN KEY (note_set_id) REFERENCES note_sets (set_id) ON DELETE CASCADE
        )
    ''')
    
    # Get all note_sets first
    cursor.execute('SELECT set_id, slug, combine_unisons FROM note_sets')
    note_sets = cursor.fetchall()
    
    # Generate cartesian product of kind and note_sets
    combinations = itertools.product(
        CONFIG['melodic_intervals_kind'],
        note_sets
    )
    
    # Insert all combinations
    for kind, (note_set_id, note_slug, combine_unisons) in combinations:
        kind_abbrev = "kq" if kind == "quality" else "kd"
        slug = f"{note_slug}_{kind_abbrev}"
        description = f"{kind}_{note_slug}"
        cursor.execute('''
            INSERT INTO melodic_interval_sets (kind, note_set_id, slug, description)
            VALUES (?, ?, ?, ?)
        ''', (kind, note_set_id, slug, description))
    
    count = cursor.rowcount
    print(f"Created {count} melodic interval sets")

if __name__ == "__main__":
    init_database()