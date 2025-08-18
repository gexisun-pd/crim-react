import os
import sys
from typing import List, Dict, Optional
import pandas as pd

# Add the core directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db.db import PiecesDB
from crim_cache_manager import cache_manager
from utils.note_id_updater import NoteIdUpdater

# Import crim_intervals for melodic ngrams extraction
try:
    import crim_intervals
    from crim_intervals import CorpusBase
    CRIM_INTERVALS_AVAILABLE = True
except ImportError:
    print("Error: crim_intervals library is required but not available.")
    print("Please install crim_intervals")
    CRIM_INTERVALS_AVAILABLE = False

def extract_melodic_ngrams_from_piece(file_path: str, piece_id: int, ngram_set_id: int, 
                                     melodic_interval_set_id: int, ngrams_number: int,
                                     combine_unisons: bool, kind: str, 
                                     ngram_set_slug: str) -> Optional[List[Dict]]:
    """Extract melodic n-grams from a piece using specific parameters"""
    if not CRIM_INTERVALS_AVAILABLE:
        raise ImportError("crim_intervals library is required for melodic n-grams extraction")
    
    filename = os.path.basename(file_path)
    piece_key = cache_manager._get_piece_key(filename)
    
    print(f"  Processing melodic n-grams for piece: {piece_key}")
    print(f"    Set: {ngram_set_slug} (n={ngrams_number}, kind={kind}, combine_unisons={combine_unisons})")
    
    # Try to load cached melodic n-grams first
    cached_ngrams = cache_manager.load_stage_cache('melodic_ngrams', 'pkl', ngram_set_slug, piece_key)
    
    if cached_ngrams is not None:
        metadata = cached_ngrams.get('metadata', {})
        print(f"  Using cached melodic n-grams from set {ngram_set_slug}")
        
        # Convert cached dataframe to list
        ngrams_df = cached_ngrams.get('ngrams')
        if ngrams_df is not None and not ngrams_df.empty:
            return convert_melodic_ngrams_to_list(ngrams_df, piece_id, ngram_set_id, ngrams_number)
    
    try:
        print(f"  Creating corpus for melodic n-grams...")
        
        # Create a corpus with just this piece
        corpus = CorpusBase([file_path])
        
        # Access the piece from corpus.scores
        if not hasattr(corpus, 'scores') or len(corpus.scores) == 0:
            print(f"  Error: No scores found in corpus")
            return []
        
        piece = corpus.scores[0]
        
        print(f"  Extracting melodic n-grams using CRIM intervals...")
        print(f"    Steps: notes -> melodic -> ngrams")
        print(f"    Parameters: combineUnisons={combine_unisons}, kind={kind}, n={ngrams_number}, end=False")
        
        # Map kind to CRIM parameter
        kind_map = {
            'quality': 'q',    # Diatonic with quality (P8, M3, m3, -m2, etc.)
            'diatonic': 'd'    # Diatonic without quality (8, 3, -2, etc.)
        }
        
        crim_kind = kind_map.get(kind, 'q')
        print(f"    CRIM kind parameter: {crim_kind}")
        
        try:
            # Step 1: Extract notes with specified combineUnisons parameter
            print(f"    Step 1: Extracting notes (combineUnisons={combine_unisons})")
            notes_df = piece.notes(combineUnisons=combine_unisons)
            print(f"    Notes shape: {notes_df.shape}")
            
            # Step 2: Extract melodic intervals using the notes DataFrame
            print(f"    Step 2: Extracting melodic intervals (kind={crim_kind}, end=False)")
            melodic_df = piece.melodic(df=notes_df, kind=crim_kind, end=False)
            print(f"    Melodic intervals shape: {melodic_df.shape}")
            
            # Step 3: Extract n-grams using the melodic intervals DataFrame
            print(f"    Step 3: Extracting {ngrams_number}-grams")
            ngrams_df = piece.ngrams(df=melodic_df, n=ngrams_number)
            print(f"    N-grams shape: {ngrams_df.shape}")
            print(f"    N-grams columns: {list(ngrams_df.columns)}")
            
        except Exception as e:
            print(f"    Error extracting melodic n-grams: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        if ngrams_df is None or ngrams_df.empty:
            print(f"  Warning: No melodic n-grams found in {file_path}")
            return []
        
        # Save melodic n-grams to cache with metadata
        metadata = {
            'file_path': file_path,
            'piece_id': piece_id,
            'ngram_set_id': ngram_set_id,
            'melodic_interval_set_id': melodic_interval_set_id,
            'ngrams_number': ngrams_number,
            'kind': kind,
            'combine_unisons': combine_unisons,
            'ngram_set_slug': ngram_set_slug,
            'extraction_method': 'crim_intervals_ngrams',
            'end_parameter': False
        }
        
        # Save to cache
        data_dict = {'ngrams': ngrams_df}
        cache_manager.save_stage_cache('melodic_ngrams', 'pkl', ngram_set_slug, piece_key, data_dict, metadata)
        print(f"  Saved melodic n-grams to cache (shape: {ngrams_df.shape})")
        
        return convert_melodic_ngrams_to_list(ngrams_df, piece_id, ngram_set_id, ngrams_number)
        
    except Exception as e:
        print(f"  Error extracting melodic n-grams from {file_path}: {e}")
        import traceback
        traceback.print_exc()
        raise

def convert_melodic_ngrams_to_list(ngrams_df: pd.DataFrame, piece_id: int, ngram_set_id: int, n_length: int) -> List[Dict]:
    """
    Convert melodic n-grams DataFrame to list of dictionaries
    
    This function processes CRIM's n-grams output and converts it to database records.
    """
    ngrams_list = []
    
    if ngrams_df is None or ngrams_df.empty:
        print(f"  Error: No valid n-grams dataframe found")
        return []
    
    print(f"  Converting melodic n-grams DataFrame to list...")
    print(f"  DataFrame columns: {list(ngrams_df.columns)}")
    print(f"  DataFrame index: {ngrams_df.index.names if hasattr(ngrams_df.index, 'names') else 'Single index'}")
    
    # Get voice columns (exclude metadata columns)
    metadata_cols = ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']
    voice_columns = [col for col in ngrams_df.columns if col not in metadata_cols]
    
    print(f"  Voice columns found: {voice_columns}")
    
    # Iterate through each row (time point) of the DataFrame
    for idx, row in ngrams_df.iterrows():
        # Extract timing information
        offset = idx
        
        # Check if we have multi-index or columns with timing info
        if isinstance(ngrams_df.index, pd.MultiIndex):
            # Multi-index case (Offset, Measure, Beat)
            if len(idx) >= 1:
                offset = idx[0]
        else:
            # Single index, check for timing columns
            if 'Offset' in ngrams_df.columns:
                offset = row.get('Offset')
        
        # Process each voice at this time point
        for voice_idx, voice_name in enumerate(voice_columns, 1):
            ngram_value = ngrams_df.loc[idx, voice_name]
            
            # Skip if no n-gram value
            if pd.isna(ngram_value) or ngram_value == '' or ngram_value is None:
                continue
            
            # Convert n-gram value to string representation
            ngram_pattern = str(ngram_value)
            
            # Create n-gram record
            ngram_data = {
                'piece_id': piece_id,
                'melodic_ngram_set_id': ngram_set_id,
                'voice': voice_idx,
                'onset': float(offset),
                'ngram': ngram_pattern,
                'voice_name': voice_name,
                'ngram_length': n_length
            }
            
            ngrams_list.append(ngram_data)
    
    print(f"  Converted to {len(ngrams_list)} melodic n-gram records")
    return ngrams_list

def create_melodic_ngrams_table():
    """Create a table for storing melodic n-grams in the database"""
    db = PiecesDB()
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS melodic_ngrams (
        ngram_id INTEGER PRIMARY KEY AUTOINCREMENT,
        piece_id INTEGER NOT NULL,
        melodic_ngram_set_id INTEGER NOT NULL,
        voice INTEGER NOT NULL,
        onset REAL NOT NULL,             -- N-gram onset time
        ngram TEXT NOT NULL,             -- N-gram pattern (e.g., "P1,M2,m3" or "1,2,3")
        ngram_length INTEGER NOT NULL,   -- Length of the n-gram
        voice_name TEXT,                 -- Voice name
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (piece_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
        FOREIGN KEY (melodic_ngram_set_id) REFERENCES melodic_ngram_sets (set_id) ON DELETE CASCADE
    );
    
    CREATE INDEX IF NOT EXISTS idx_melodic_ngrams_piece ON melodic_ngrams(piece_id);
    CREATE INDEX IF NOT EXISTS idx_melodic_ngrams_set ON melodic_ngrams(melodic_ngram_set_id);
    CREATE INDEX IF NOT EXISTS idx_melodic_ngrams_voice ON melodic_ngrams(voice);
    CREATE INDEX IF NOT EXISTS idx_melodic_ngrams_onset ON melodic_ngrams(onset);
    CREATE INDEX IF NOT EXISTS idx_melodic_ngrams_pattern ON melodic_ngrams(ngram);
    CREATE INDEX IF NOT EXISTS idx_melodic_ngrams_length ON melodic_ngrams(ngram_length);
    """
    
    try:
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.executescript(create_table_sql)
        conn.commit()
        conn.close()
        print("Melodic n-grams table created successfully")
    except Exception as e:
        print(f"Error creating melodic n-grams table: {e}")
        if 'conn' in locals():
            conn.close()
        raise

def insert_melodic_ngrams_batch(ngrams_list: List[Dict]) -> int:
    """Insert a batch of melodic n-grams into the database"""
    if not ngrams_list:
        return 0
    
    db = PiecesDB()
    
    insert_sql = """
    INSERT INTO melodic_ngrams (
        piece_id, melodic_ngram_set_id, voice, onset, ngram, ngram_length, voice_name, note_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    values_list = []
    for ngram in ngrams_list:
        values = (
            ngram.get('piece_id'),
            ngram.get('melodic_ngram_set_id'),
            ngram.get('voice'),
            ngram.get('onset'),
            ngram.get('ngram'),
            ngram.get('ngram_length'),
            ngram.get('voice_name'),
            ngram.get('note_id')
        )
        values_list.append(values)
    
    try:
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.executemany(insert_sql, values_list)
        conn.commit()
        conn.close()
        return len(values_list)
    except Exception as e:
        print(f"Error inserting melodic n-grams: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return 0

def melodic_ngrams_exist_for_piece_and_set(piece_id: int, ngram_set_id: int) -> bool:
    """Check if melodic n-grams already exist for a piece and n-gram set"""
    db = PiecesDB()
    
    try:
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM melodic_ngrams 
            WHERE piece_id = ? AND melodic_ngram_set_id = ?
        """, (piece_id, ngram_set_id))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        print(f"Error checking melodic n-grams existence: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def ingest_melodic_ngrams_for_all_pieces():
    """Main function to ingest melodic n-grams for all pieces using all melodic n-gram sets (entry=False only)"""
    
    # Check if crim_intervals is available before proceeding
    if not CRIM_INTERVALS_AVAILABLE:
        print("Cannot proceed without crim_intervals library.")
        return
    
    # Create the melodic n-grams table if it doesn't exist
    print("Creating melodic n-grams table...")
    create_melodic_ngrams_table()
    
    # Initialize database connection
    db = PiecesDB()
    
    # Get all pieces from database
    print("Retrieving all pieces from database...")
    pieces = db.get_all_pieces()
    
    if not pieces:
        print("No pieces found in database.")
        print("Please run ingest_pieces.py first to add pieces to the database.")
        return
    
    print(f"Found {len(pieces)} pieces in database")
    
    # Get all melodic n-gram sets (only entry=False)
    print("Retrieving all melodic n-gram sets (entry=False only)...")
    ngram_sets = db.get_all_melodic_ngram_sets_non_entry()
    
    if not ngram_sets:
        print("No melodic n-gram sets found in database.")
        print("Please run core/db/init_db.py first to create parameter sets.")
        return
    
    print(f"Found {len(ngram_sets)} melodic n-gram sets (entry=False):")
    for ngram_set in ngram_sets:
        print(f"  Set {ngram_set['set_id']}: {ngram_set['slug']} (n={ngram_set['ngrams_number']}, entry={ngram_set['ngrams_entry']})")
    
    # Get project root directory (two levels up from core/ingest/)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_root = os.path.join(project_root, 'data')
    
    total_combinations = len(pieces) * len(ngram_sets)
    processed_count = 0
    skipped_count = 0
    error_count = 0
    total_ngrams = 0
    
    print(f"\n=== Processing {total_combinations} combinations (pieces × n-gram sets) ===")
    
    # Process each melodic n-gram set
    for ngram_set in ngram_sets:
        ngram_set_id = ngram_set['set_id']
        ngram_slug = ngram_set['slug']
        melodic_interval_set_id = ngram_set['melodic_interval_set_id']
        ngrams_number = ngram_set['ngrams_number']
        ngrams_entry = ngram_set['ngrams_entry']
        
        # Get the corresponding melodic interval set to find kind and note_set info
        melodic_sets = db.get_all_melodic_interval_sets()
        melodic_set = next((ms for ms in melodic_sets if ms['set_id'] == melodic_interval_set_id), None)
        if not melodic_set:
            print(f"Error: Could not find melodic interval set with id {melodic_interval_set_id}")
            continue
        
        kind = melodic_set['kind']
        note_set_id = melodic_set['note_set_id']
        
        # Get the corresponding note set to find combine_unisons value
        note_sets = db.get_all_note_sets()
        note_set = next((ns for ns in note_sets if ns['set_id'] == note_set_id), None)
        if not note_set:
            print(f"Error: Could not find note set with id {note_set_id}")
            continue
            
        combine_unisons = note_set['combine_unisons']
        
        print(f"\n--- Processing Melodic N-gram Set {ngram_set_id}: {ngram_slug} ---")
        print(f"N-grams: {ngrams_number}, Entry: {ngrams_entry}, Kind: {kind}, Combine Unisons: {combine_unisons}")
        
        set_processed = 0
        set_skipped = 0
        set_errors = 0
        set_ngrams = 0
        
        # Process each piece with this melodic n-gram set
        for i, piece in enumerate(pieces, 1):
            piece_id = piece['piece_id']
            piece_path = piece['path']
            piece_filename = piece['filename']
            
            print(f"Processing piece {i}: {piece_filename} (Set {ngram_set_id})")
            
            try:
                # Check if melodic n-grams already exist for this piece and set
                if melodic_ngrams_exist_for_piece_and_set(piece_id, ngram_set_id):
                    print(f"  Skipping - melodic n-grams already exist for piece {piece_id} with set {ngram_set_id}")
                    skipped_count += 1
                    set_skipped += 1
                    continue
                
                # Construct full file path
                full_file_path = os.path.join(data_root, piece_path)
                
                if not os.path.exists(full_file_path):
                    print(f"  Error: File not found: {full_file_path}")
                    error_count += 1
                    set_errors += 1
                    continue
                
                # Extract melodic n-grams from the piece
                ngrams_list = extract_melodic_ngrams_from_piece(
                    full_file_path, piece_id, ngram_set_id, melodic_interval_set_id,
                    ngrams_number, combine_unisons, kind, ngram_slug
                )
                
                if not ngrams_list:
                    print(f"  Warning: No melodic n-grams extracted from {piece_filename}")
                    processed_count += 1  # Still count as processed
                    set_processed += 1
                    continue
                
                # Insert melodic n-grams into database
                print(f"  Inserting {len(ngrams_list)} melodic n-grams into database...")
                success_count = insert_melodic_ngrams_batch(ngrams_list)
                
                if success_count == len(ngrams_list):
                    print(f"  Successfully inserted {success_count} melodic n-grams")
                    processed_count += 1
                    set_processed += 1
                    total_ngrams += success_count
                    set_ngrams += success_count
                else:
                    print(f"  Warning: Only {success_count}/{len(ngrams_list)} melodic n-grams inserted")
                    error_count += 1
                    set_errors += 1
                    
            except Exception as e:
                print(f"  Error processing piece {piece_id}: {e}")
                error_count += 1
                set_errors += 1
                continue
        
        # Print set summary
        print(f"\n--- Set {ngram_set_id} Summary ---")
        print(f"Successfully processed: {set_processed}")
        print(f"Skipped (already exists): {set_skipped}")
        print(f"Errors: {set_errors}")
        print(f"N-grams inserted: {set_ngrams}")
    
    # Print overall summary
    print(f"\n============================================================")
    print(f"=== Overall Melodic N-grams Ingestion Summary ===")
    print(f"Total melodic n-gram sets: {len(ngram_sets)}")
    print(f"Total pieces: {len(pieces)}")
    print(f"Total combinations processed: {processed_count}")
    print(f"Total combinations skipped: {skipped_count}")
    print(f"Total errors: {error_count}")
    print(f"Total melodic n-grams inserted: {total_ngrams}")
    
    # Print cache statistics
    print(f"\n=== Cache Statistics ===")
    stats = cache_manager.get_cache_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Update note_id fields for newly inserted melodic n-grams
    print(f"\n=== Updating note_id fields ===")
    try:
        updater = NoteIdUpdater()
        updated_count = updater.update_note_ids_batch_optimized('melodic_ngrams')
        print(f"Updated {updated_count} melodic n-grams with note_id references")
    except Exception as e:
        print(f"Error updating note_id fields: {e}")

if __name__ == "__main__":
    ingest_melodic_ngrams_for_all_pieces()
