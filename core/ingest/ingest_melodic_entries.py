import os
import sys
import sqlite3
import traceback
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

def extract_melodic_entries_from_piece(file_path: str, piece_id: int, ngram_set_id: int, 
                                     melodic_interval_set_id: int, ngrams_number: int,
                                     combine_unisons: bool, kind: str, 
                                     ngram_set_slug: str) -> Optional[List[Dict]]:
    """Extract melodic entries from a piece using specific parameters and CRIM entries() function"""
    if not CRIM_INTERVALS_AVAILABLE:
        raise ImportError("crim_intervals library is required for melodic entries extraction")
    
    filename = os.path.basename(file_path)
    piece_key = cache_manager._get_piece_key(filename)
    
    print(f"  Processing melodic entries for piece: {piece_key}")
    print(f"    Set: {ngram_set_slug} (n={ngrams_number}, kind={kind}, combine_unisons={combine_unisons})")
    
    # Try to load cached melodic entries first
    cached_entries = cache_manager.load_stage_cache('melodic_entries', 'pkl', ngram_set_slug, piece_key)
    
    if cached_entries is not None:
        metadata = cached_entries.get('metadata', {})
        print(f"  Using cached melodic entries from set {ngram_set_slug}")
        
        # Convert cached dataframe to list
        entries_df = cached_entries.get('entries')
        if entries_df is not None and not entries_df.empty:
            return convert_melodic_entries_to_list(entries_df, piece_id, ngram_set_id, ngrams_number)
    
    try:
        print(f"  Creating corpus for melodic entries...")
        
        # Create a corpus with just this piece
        corpus = CorpusBase([file_path])
        
        # Access the piece from corpus.scores
        if not hasattr(corpus, 'scores') or len(corpus.scores) == 0:
            print(f"  Error: No scores found in corpus")
            return []
        
        piece = corpus.scores[0]
        
        print(f"  Extracting melodic entries using CRIM intervals...")
        print(f"    Steps: notes -> melodic -> entries")
        print(f"    Parameters: combineUnisons={combine_unisons}, kind={kind}, n={ngrams_number}")
        print(f"    Entry parameters: end=False, thematic=False, anywhere=True, fermatas=True")
        
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
            
            # Step 2: Extract melodic intervals using the notes DataFrame with end=False
            print(f"    Step 2: Extracting melodic intervals (kind={crim_kind}, end=False)")
            melodic_df = piece.melodic(df=notes_df, kind=crim_kind, end=False)
            print(f"    Melodic intervals shape: {melodic_df.shape}")
            
            # Step 3: Extract entries using the melodic intervals DataFrame
            print(f"    Step 3: Extracting {ngrams_number}-gram entries with specified parameters")
            # CRIM entries() 默认 offsets='first'，end=False，无需显式传递
            # 只需传递 df, n, thematic, anywhere, fermatas 参数
            entries_df = piece.entries(
                df=melodic_df, 
                n=ngrams_number,
                thematic=False,      # Don't require thematic (multiple occurrences)
                anywhere=True,       # Include all instances, not just from rests
                fermatas=True        # Include entries after fermatas
            )
            print(f"    Entries shape: {entries_df.shape}")
            print(f"    Entries columns: {list(entries_df.columns)}")
            
        except Exception as e:
            print(f"    Error extracting melodic entries: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        if entries_df is None or entries_df.empty:
            print(f"  Warning: No melodic entries found in {file_path}")
            return []
        
        # Save melodic entries to cache with metadata
        metadata = {
            'file_path': file_path,
            'piece_id': piece_id,
            'ngram_set_id': ngram_set_id,
            'melodic_interval_set_id': melodic_interval_set_id,
            'ngrams_number': ngrams_number,
            'kind': kind,
            'combine_unisons': combine_unisons,
            'ngram_set_slug': ngram_set_slug,
            'extraction_method': 'crim_intervals_entries',
            'end_parameter': False,
            'thematic': False,
            'anywhere': True,
            'fermatas': True,
            'offsets': 'first'
        }
        
        # Save to cache
        data_dict = {'entries': entries_df}
        cache_manager.save_stage_cache('melodic_entries', 'pkl', ngram_set_slug, piece_key, data_dict, metadata)
        print(f"  Saved melodic entries to cache (shape: {entries_df.shape})")
        
        return convert_melodic_entries_to_list(entries_df, piece_id, ngram_set_id, ngrams_number)
        
    except Exception as e:
        print(f"  Error extracting melodic entries from {file_path}: {e}")
        import traceback
        traceback.print_exc()
        raise

def convert_melodic_entries_to_list(entries_df: pd.DataFrame, piece_id: int, ngram_set_id: int, n_length: int) -> List[Dict]:
    """
    Convert melodic entries DataFrame to list of dictionaries
    
    This function processes CRIM's entries output and converts it to database records.
    """
    entries_list = []
    
    if entries_df is None or entries_df.empty:
        print(f"  Error: No valid entries dataframe found")
        return []
    
    print(f"  Converting melodic entries DataFrame to list...")
    print(f"  DataFrame columns: {list(entries_df.columns)}")
    print(f"  DataFrame index: {entries_df.index.names if hasattr(entries_df.index, 'names') else 'Single index'}")
    
    # Get voice columns (exclude metadata columns)
    metadata_cols = ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']
    voice_columns = [col for col in entries_df.columns if col not in metadata_cols]
    
    print(f"  Voice columns found: {voice_columns}")
    
    # Iterate through each row (time point) of the DataFrame
    for idx, row in entries_df.iterrows():
        # Extract timing information
        offset = idx
        
        # Check if we have multi-index or columns with timing info
        if isinstance(entries_df.index, pd.MultiIndex):
            # Multi-index case (Offset, Measure, Beat)
            if len(idx) >= 1:
                offset = idx[0]
        else:
            # Single index, check for timing columns
            if 'Offset' in entries_df.columns:
                offset = row.get('Offset')
        
        # Process each voice at this time point
        for voice_idx, voice_name in enumerate(voice_columns, 1):
            entry_value = entries_df.loc[idx, voice_name]
            
            # Skip if no entry value
            if pd.isna(entry_value) or entry_value == '' or entry_value is None:
                continue
            
            # Convert entry value to string representation
            entry_pattern = str(entry_value)
            
            # Create entry record
            entry_data = {
                'piece_id': piece_id,
                'melodic_ngram_set_id': ngram_set_id,
                'voice': voice_idx,
                'onset': float(offset),
                'entry_pattern': entry_pattern,
                'voice_name': voice_name,
                'entry_length': n_length,
                'is_thematic': False,  # Set based on CRIM parameters
                'from_rest': True     # Entries typically start from rests/breaks
            }
            
            entries_list.append(entry_data)
    
    print(f"  Converted to {len(entries_list)} melodic entry records")
    return entries_list

def create_melodic_entries_table():
    """Create a table for storing melodic entries in the database"""
    db = PiecesDB()
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS melodic_entries (
        entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
        piece_id INTEGER NOT NULL,
        melodic_ngram_set_id INTEGER NOT NULL,
        voice INTEGER NOT NULL,
        onset REAL NOT NULL,             -- Entry onset time
        entry_pattern TEXT NOT NULL,     -- Entry pattern (e.g., "P1,M2,m3" or "1,2,3")
        entry_length INTEGER NOT NULL,   -- Length of the entry
        voice_name TEXT,                 -- Voice name
        is_thematic BOOLEAN NOT NULL DEFAULT 0, -- Whether this entry is thematic
        from_rest BOOLEAN NOT NULL DEFAULT 1,   -- Whether this entry starts after rest/break/fermata
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (piece_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
        FOREIGN KEY (melodic_ngram_set_id) REFERENCES melodic_ngram_sets (set_id) ON DELETE CASCADE
    );
    
    CREATE INDEX IF NOT EXISTS idx_melodic_entries_piece ON melodic_entries(piece_id);
    CREATE INDEX IF NOT EXISTS idx_melodic_entries_set ON melodic_entries(melodic_ngram_set_id);
    CREATE INDEX IF NOT EXISTS idx_melodic_entries_voice ON melodic_entries(voice);
    CREATE INDEX IF NOT EXISTS idx_melodic_entries_onset ON melodic_entries(onset);
    CREATE INDEX IF NOT EXISTS idx_melodic_entries_pattern ON melodic_entries(entry_pattern);
    CREATE INDEX IF NOT EXISTS idx_melodic_entries_length ON melodic_entries(entry_length);
    CREATE INDEX IF NOT EXISTS idx_melodic_entries_thematic ON melodic_entries(is_thematic);
    CREATE INDEX IF NOT EXISTS idx_melodic_entries_from_rest ON melodic_entries(from_rest);
    """
    
    try:
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.executescript(create_table_sql)
        conn.commit()
        conn.close()
        print("Melodic entries table created successfully")
    except Exception as e:
        print(f"Error creating melodic entries table: {e}")
        if 'conn' in locals():
            conn.close()
        raise

def insert_melodic_entries_batch(entries_list: List[Dict]) -> int:
    """Insert a batch of melodic entries into the database"""
    if not entries_list:
        return 0
    
    db = PiecesDB()
    
    insert_sql = """
    INSERT INTO melodic_entries (
        piece_id, melodic_ngram_set_id, voice, onset, entry_pattern, entry_length, voice_name, is_thematic, from_rest, note_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    values_list = []
    for entry in entries_list:
        values = (
            entry.get('piece_id'),
            entry.get('melodic_ngram_set_id'),
            entry.get('voice'),
            entry.get('onset'),
            entry.get('entry_pattern'),
            entry.get('entry_length'),
            entry.get('voice_name'),
            entry.get('is_thematic', False),
            entry.get('from_rest', True),
            entry.get('note_id')  # Include note_id field
        )
        values_list.append(values)
    
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.executemany(insert_sql, values_list)
        conn.commit()
        conn.close()
        return len(values_list)
    except Exception as e:
        print(f"Error inserting melodic entries: {e}")
        if 'conn' in locals():
            conn.close()
        return 0

def melodic_entries_exist_for_piece_and_set(piece_id: int, ngram_set_id: int) -> bool:
    """Check if melodic entries already exist for a piece and n-gram set"""
    db = PiecesDB()
    
    try:
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM melodic_entries 
            WHERE piece_id = ? AND melodic_ngram_set_id = ?
        """, (piece_id, ngram_set_id))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        print(f"Error checking melodic entries existence: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def ingest_melodic_entries_for_all_pieces():
    """Main function to ingest melodic entries for all pieces using all melodic n-gram sets (entry=True only)"""
    
    # Check if crim_intervals is available before proceeding
    if not CRIM_INTERVALS_AVAILABLE:
        print("Cannot proceed without crim_intervals library.")
        return
    
    # Create the melodic entries table if it doesn't exist
    print("Creating melodic entries table...")
    create_melodic_entries_table()
    
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
    
    # Get all melodic n-gram sets (only entry=True)
    print("Retrieving all melodic n-gram sets (entry=True only)...")
    ngram_sets = db.get_all_melodic_ngram_sets_entry_only()
    
    if not ngram_sets:
        print("No melodic n-gram sets (entry=True) found in database.")
        print("Please run core/db/init_db.py first to create parameter sets.")
        return
    
    print(f"Found {len(ngram_sets)} melodic n-gram sets (entry=True):")
    for ngram_set in ngram_sets:
        print(f"  Set {ngram_set['set_id']}: {ngram_set['slug']} (n={ngram_set['ngrams_number']}, entry={ngram_set['ngrams_entry']})")
    
    # Get project root directory (two levels up from core/ingest/)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_root = os.path.join(project_root, 'data')
    
    total_combinations = len(pieces) * len(ngram_sets)
    processed_count = 0
    skipped_count = 0
    error_count = 0
    total_entries = 0
    
    print(f"\n=== Processing {total_combinations} combinations (pieces × entry sets) ===")
    
    # Process each melodic entry set
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
        
        print(f"\n--- Processing Melodic Entry Set {ngram_set_id}: {ngram_slug} ---")
        print(f"N-grams: {ngrams_number}, Entry: {ngrams_entry}, Kind: {kind}, Combine Unisons: {combine_unisons}")
        
        set_processed = 0
        set_skipped = 0
        set_errors = 0
        set_entries = 0
        
        # Process each piece with this melodic entry set
        for i, piece in enumerate(pieces, 1):
            piece_id = piece['piece_id']
            piece_path = piece['path']
            piece_filename = piece['filename']
            
            print(f"Processing piece {i}: {piece_filename} (Set {ngram_set_id})")
            
            try:
                # Check if melodic entries already exist for this piece and set
                if melodic_entries_exist_for_piece_and_set(piece_id, ngram_set_id):
                    print(f"  Skipping - melodic entries already exist for piece {piece_id} with set {ngram_set_id}")
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
                
                # Extract melodic entries from the piece
                entries_list = extract_melodic_entries_from_piece(
                    full_file_path, piece_id, ngram_set_id, melodic_interval_set_id,
                    ngrams_number, combine_unisons, kind, ngram_slug
                )
                
                if not entries_list:
                    print(f"  Warning: No melodic entries extracted from {piece_filename}")
                    processed_count += 1  # Still count as processed
                    set_processed += 1
                    continue
                
                # Insert melodic entries into database
                print(f"  Inserting {len(entries_list)} melodic entries into database...")
                success_count = insert_melodic_entries_batch(entries_list)
                
                if success_count == len(entries_list):
                    print(f"  Successfully inserted {success_count} melodic entries")
                    processed_count += 1
                    set_processed += 1
                    total_entries += success_count
                    set_entries += success_count
                else:
                    print(f"  Warning: Only {success_count}/{len(entries_list)} melodic entries inserted")
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
        print(f"Entries inserted: {set_entries}")
    
    # Print overall summary
    print(f"\n============================================================")
    print(f"=== Overall Melodic Entries Ingestion Summary ===")
    print(f"Total melodic entry sets: {len(ngram_sets)}")
    print(f"Total pieces: {len(pieces)}")
    print(f"Total combinations processed: {processed_count}")
    print(f"Total combinations skipped: {skipped_count}")
    print(f"Total errors: {error_count}")
    print(f"Total melodic entries inserted: {total_entries}")
    
    # Print cache statistics
    print(f"\n=== Cache Statistics ===")
    stats = cache_manager.get_cache_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Update note_id fields for newly inserted melodic entries
    print(f"\n=== Updating note_id fields ===")
    try:
        updater = NoteIdUpdater()
        updated_count = updater.update_note_ids_batch_optimized('melodic_entries')
        print(f"Updated {updated_count} melodic entries with note_id references")
    except Exception as e:
        print(f"Error updating note_id fields: {e}")

if __name__ == "__main__":
    ingest_melodic_entries_for_all_pieces()
