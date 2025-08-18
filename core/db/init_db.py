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
    
    # Check if database exists
    db_exists = os.path.exists(db_path)
    
    if db_exists:
        print(f"Database already exists at {db_path}")
        print("Preserving existing data...")
    else:
        print(f"Creating new database at {db_path}")
    
    # Create connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Read and execute schema (this will create tables if they don't exist)
    with open(schema_path, 'r') as f:
        schema = f.read()
        cursor.executescript(schema)
    
    # Generate and insert note_sets (only if not exists)
    create_note_sets(cursor)
    
    # Generate and insert melodic_interval_sets (only if not exists)
    create_melodic_interval_sets(cursor)
    
    # Generate and insert melodic_ngram_sets (only if not exists)
    create_melodic_ngram_sets(cursor)
    
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
    
    # Check if data already exists
    cursor.execute('SELECT COUNT(*) FROM note_sets')
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"Note sets already exist ({existing_count} sets), skipping creation")
        return
    
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
    # Create melodic_interval_sets table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS melodic_interval_sets (
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
    
    # Check if data already exists
    cursor.execute('SELECT COUNT(*) FROM melodic_interval_sets')
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"Melodic interval sets already exist ({existing_count} sets), skipping creation")
        return
    
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

def create_melodic_ngram_sets(cursor):
    """Create melodic_ngram_sets table with all combinations of melodic_interval_sets and ngram parameters"""
    # Create melodic_ngram_sets table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS melodic_ngram_sets (
            set_id INTEGER PRIMARY KEY AUTOINCREMENT,
            melodic_interval_set_id INTEGER NOT NULL,
            ngrams_number INTEGER NOT NULL,
            ngrams_entry BOOLEAN NOT NULL,
            parent_set_id INTEGER,
            slug TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(melodic_interval_set_id, ngrams_number, ngrams_entry),
            FOREIGN KEY (melodic_interval_set_id) REFERENCES melodic_interval_sets (set_id) ON DELETE CASCADE,
            FOREIGN KEY (parent_set_id) REFERENCES melodic_ngram_sets (set_id) ON DELETE CASCADE
        )
    ''')
    
    # Check if data already exists
    cursor.execute('SELECT COUNT(*) FROM melodic_ngram_sets')
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"Melodic ngram sets already exist ({existing_count} sets), skipping creation")
        return
    
    # Get all melodic_interval_sets first
    cursor.execute('SELECT set_id, slug, kind FROM melodic_interval_sets')
    melodic_interval_sets = cursor.fetchall()
    
    # First, create all parent sets (ngrams_entry = False)
    parent_sets = {}  # key: (interval_set_id, ngrams_number), value: set_id
    
    for (interval_set_id, interval_slug, kind), ngrams_number in itertools.product(
        melodic_interval_sets, CONFIG['melodic_ngrams_number']
    ):
        entry_abbrev = "eF"  # Always False for parent sets
        slug = f"{interval_slug}_n{ngrams_number}_{entry_abbrev}"
        description = f"{interval_slug}_ngrams{ngrams_number}_entryFalse"
        
        cursor.execute('''
            INSERT INTO melodic_ngram_sets (melodic_interval_set_id, ngrams_number, ngrams_entry, parent_set_id, slug, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (interval_set_id, ngrams_number, False, None, slug, description))
        
        # Store the parent set_id for later reference
        parent_set_id = cursor.lastrowid
        parent_sets[(interval_set_id, ngrams_number)] = parent_set_id
    
    # Then, create all child sets (ngrams_entry = True) with parent_set_id
    for (interval_set_id, interval_slug, kind), ngrams_number in itertools.product(
        melodic_interval_sets, CONFIG['melodic_ngrams_number']
    ):
        # Get the corresponding parent set_id
        parent_set_id = parent_sets[(interval_set_id, ngrams_number)]
        
        entry_abbrev = "eT"  # Always True for child sets
        slug = f"{interval_slug}_n{ngrams_number}_{entry_abbrev}"
        description = f"{interval_slug}_ngrams{ngrams_number}_entryTrue"
        
        cursor.execute('''
            INSERT INTO melodic_ngram_sets (melodic_interval_set_id, ngrams_number, ngrams_entry, parent_set_id, slug, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (interval_set_id, ngrams_number, True, parent_set_id, slug, description))
    
    # Count total created sets
    cursor.execute('SELECT COUNT(*) FROM melodic_ngram_sets')
    total_count = cursor.fetchone()[0]
    print(f"Created {total_count} melodic ngram sets ({total_count//2} parent sets, {total_count//2} child sets)")

def reset_parameter_sets():
    """Reset only parameter sets tables, preserving all data tables"""
    db_path = os.path.join(project_root, 'database', 'analysis.db')
    
    if not os.path.exists(db_path):
        print("Database does not exist. Run init_database() first.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Resetting parameter sets while preserving data...")
    
    # Drop and recreate parameter set tables in correct order (respecting foreign keys)
    cursor.execute('DROP TABLE IF EXISTS melodic_ngram_sets')
    cursor.execute('DROP TABLE IF EXISTS melodic_interval_sets') 
    cursor.execute('DROP TABLE IF EXISTS note_sets')
    
    # Recreate parameter sets
    create_note_sets(cursor)
    create_melodic_interval_sets(cursor) 
    create_melodic_ngram_sets(cursor)
    
    conn.commit()
    conn.close()
    print("Parameter sets reset successfully")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Initialize database')
    parser.add_argument('--reset-params', action='store_true',
                       help='Reset only parameter sets, preserve data')
    args = parser.parse_args()
    
    if args.reset_params:
        reset_parameter_sets()
    else:
        init_database()