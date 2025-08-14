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
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(combine_unisons)
        )
    ''')
    
    # Clear existing data
    cursor.execute('DELETE FROM note_sets')
    
    # Insert all combinations
    for combine_unisons in CONFIG['notes_combine_unisons']:
        description = f"combine_unisons_{combine_unisons}"
        cursor.execute('''
            INSERT INTO note_sets (combine_unisons, description)
            VALUES (?, ?)
        ''', (combine_unisons, description))
    
    count = cursor.rowcount
    print(f"Created {count} note sets")

def create_melodic_interval_sets(cursor):
    """Create melodic_interval_sets table with all combinations of kind and combine_unisons"""
    # Create melodic_interval_sets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS melodic_interval_sets (
            set_id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            combine_unisons BOOLEAN NOT NULL,
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(kind, combine_unisons)
        )
    ''')
    
    # Clear existing data
    cursor.execute('DELETE FROM melodic_interval_sets')
    
    # Generate cartesian product of kind and combine_unisons
    combinations = itertools.product(
        CONFIG['melodic_intervals_kind'],
        CONFIG['notes_combine_unisons']
    )
    
    # Insert all combinations
    for kind, combine_unisons in combinations:
        description = f"{kind}_combine_{combine_unisons}"
        cursor.execute('''
            INSERT INTO melodic_interval_sets (kind, combine_unisons, description)
            VALUES (?, ?, ?)
        ''', (kind, combine_unisons, description))
    
    count = cursor.rowcount
    print(f"Created {count} melodic interval sets")

if __name__ == "__main__":
    init_database()