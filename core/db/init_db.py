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
    
    # First, add is_entry column to existing notes table if not exists
    if db_exists:
        try:
            cursor.execute("ALTER TABLE notes ADD COLUMN is_entry BOOLEAN DEFAULT 0")
            print("Added is_entry column to notes table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("is_entry column already exists in notes table")
            else:
                print(f"Warning: Could not add is_entry column: {e}")
    
    # Read schema and execute (this will handle creation of tables and indexes)
    with open(schema_path, 'r') as f:
        schema = f.read()
        try:
            cursor.executescript(schema)
        except sqlite3.OperationalError as e:
            if "no such column: is_entry" in str(e):
                # Try to create the index separately after ensuring column exists
                print("Handling is_entry column creation...")
                # Extract all SQL statements
                statements = [stmt.strip() for stmt in schema.split(';') if stmt.strip()]
                for stmt in statements:
                    try:
                        if 'idx_notes_is_entry' in stmt and 'is_entry' in stmt:
                            # Skip this index for now, we'll create it later
                            continue
                        cursor.execute(stmt)
                    except sqlite3.Error as inner_e:
                        if "no such column: is_entry" not in str(inner_e):
                            print(f"Warning executing statement: {inner_e}")
            else:
                raise e
    
    # Create index for is_entry column if not exists
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_is_entry ON notes(is_entry)")
        print("Created index for is_entry column")
    except sqlite3.Error as e:
        print(f"Warning: Could not create is_entry index: {e}")
    
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
            slug TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(melodic_interval_set_id, ngrams_number),
            FOREIGN KEY (melodic_interval_set_id) REFERENCES melodic_interval_sets (set_id) ON DELETE CASCADE
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
    
    # Create all sets (without entry distinction)
    for (interval_set_id, interval_slug, kind), ngrams_number in itertools.product(
        melodic_interval_sets, CONFIG['melodic_ngrams_number']
    ):
        slug = f"{interval_slug}_n{ngrams_number}"
        description = f"{interval_slug}_ngrams{ngrams_number}"
        
        cursor.execute('''
            INSERT INTO melodic_ngram_sets (melodic_interval_set_id, ngrams_number, slug, description)
            VALUES (?, ?, ?, ?)
        ''', (interval_set_id, ngrams_number, slug, description))
    
    # Count total created sets
    cursor.execute('SELECT COUNT(*) FROM melodic_ngram_sets')
    total_count = cursor.fetchone()[0]
    print(f"Created {total_count} melodic ngram sets")

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