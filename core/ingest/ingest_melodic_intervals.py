import os
import sys
from typing import List, Dict, Optional
import pandas as pd

# Add the core directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db.db import PiecesDB
from crim_cache_manager import cache_manager
from utils.note_id_updater import NoteIdUpdater

# Import crim_intervals for melodic intervals extraction
try:
    import crim_intervals
    from crim_intervals import CorpusBase
    CRIM_INTERVALS_AVAILABLE = True
except ImportError:
    print("Error: crim_intervals library is required but not available.")
    print("Please install crim_intervals")
    CRIM_INTERVALS_AVAILABLE = False

def parse_crim_interval_to_semitones(interval_str: str) -> Optional[float]:
    """Convert CRIM interval notation to semitones"""
    if not interval_str or interval_str in ['Rest', 'NaN', '']:
        return None
    
    # Handle negative (descending) intervals
    is_descending = interval_str.startswith('-')
    if is_descending:
        interval_str = interval_str[1:]  # Remove the minus sign
    
    # CRIM interval mappings to semitones
    interval_map = {
        # Perfect intervals
        'P1': 0, 'P4': 5, 'P5': 7, 'P8': 12, 'P11': 17, 'P12': 19, 'P15': 24,
        
        # Major intervals
        'M2': 2, 'M3': 4, 'M6': 9, 'M7': 11, 'M9': 14, 'M10': 16, 'M13': 21, 'M14': 23,
        
        # Minor intervals
        'm2': 1, 'm3': 3, 'm6': 8, 'm7': 10, 'm9': 13, 'm10': 15, 'm13': 20, 'm14': 22,
        
        # Augmented intervals
        'A1': 1, 'A2': 3, 'A3': 5, 'A4': 6, 'A5': 8, 'A6': 10, 'A7': 12,
        
        # Diminished intervals
        'd1': -1, 'd2': 0, 'd3': 2, 'd4': 4, 'd5': 6, 'd6': 7, 'd7': 9, 'd8': 11,
        
        # Other common intervals
        'TT': 6,  # Tritone
    }
    
    semitones = interval_map.get(interval_str)
    
    if semitones is not None:
        return -semitones if is_descending else semitones
    else:
        # Try to parse unknown format
        print(f"    Warning: Unknown interval format '{interval_str}', setting to None")
        return None

def extract_melodic_intervals_from_piece(file_path: str, piece_id: int, melodic_set_id: int, 
                                        kind: str, combine_unisons: bool, note_set_slug: str, 
                                        melodic_set_slug: str) -> Optional[List[Dict]]:
    """Extract melodic intervals from a piece using specific parameters and cached notes"""
    if not CRIM_INTERVALS_AVAILABLE:
        raise ImportError("crim_intervals library is required for melodic intervals extraction")
    
    filename = os.path.basename(file_path)
    piece_key = cache_manager._get_piece_key(filename)
    
    print(f"  Processing melodic intervals for piece: {piece_key}")
    print(f"    Set: {melodic_set_slug} (kind={kind}, combine_unisons={combine_unisons})")
    
    # Try to load cached melodic intervals first
    cached_intervals = cache_manager.load_stage_cache('melodic_intervals', 'pkl', melodic_set_slug, piece_key)
    
    if cached_intervals is not None:
        metadata = cached_intervals.get('metadata', {})
        print(f"  Using cached melodic intervals from set {melodic_set_slug}")
        
        # Convert cached dataframe to list
        interval_df = cached_intervals.get('intervals')
        if interval_df is not None and not interval_df.empty:
            return convert_melodic_intervals_to_list(interval_df, piece_id, melodic_set_id, kind)
    
    # Load the corresponding notes from cache
    notes_cached = cache_manager.load_stage_cache('notes', 'pkl', note_set_slug, piece_key)
    
    if notes_cached is None:
        print(f"  Error: Required notes cache not found for {piece_key} with set {note_set_slug}")
        print(f"  Please run ingest_notes.py first to cache the notes")
        return []
    
    notes_df = notes_cached.get('notes')
    if notes_df is None or notes_df.empty:
        print(f"  Error: No notes dataframe found in cache for {piece_key}")
        return []
    
    print(f"  Using cached notes from set {note_set_slug} (combine_unisons={combine_unisons})")
    
    try:
        print(f"  Creating corpus for melodic intervals...")
        
        # Create a corpus with just this piece
        corpus = CorpusBase([file_path])
        
        # Access the piece from corpus.scores
        if not hasattr(corpus, 'scores') or len(corpus.scores) == 0:
            print(f"  Error: No scores found in corpus")
            return []
        
        piece = corpus.scores[0]
        
        print(f"  Extracting melodic intervals using CRIM intervals...")
        print(f"    Kind: {kind}, end=False")
        
        # Extract melodic intervals using the specified kind
        # Map kind to CRIM parameter
        kind_map = {
            'quality': 'q',    # Diatonic with quality (P8, M3, m3, -m2, etc.)
            'diatonic': 'd'    # Diatonic without quality (8, 3, -2, etc.)
        }
        
        crim_kind = kind_map.get(kind, 'q')
        print(f"    CRIM kind parameter: {crim_kind}")
        
        try:
            # Use end=False to associate intervals with the first note of the pair
            melodic_df = piece.melodic(kind=crim_kind, end=False)
            print(f"    Melodic intervals shape: {melodic_df.shape}")
            print(f"    Melodic intervals columns: {list(melodic_df.columns)}")
        except Exception as e:
            print(f"    Error extracting melodic intervals: {e}")
            return []
        
        if melodic_df is None or melodic_df.empty:
            print(f"  Warning: No melodic intervals found in {file_path}")
            return []
        
        # Save melodic intervals to cache with metadata
        metadata = {
            'file_path': file_path,
            'piece_id': piece_id,
            'melodic_set_id': melodic_set_id,
            'kind': kind,
            'combine_unisons': combine_unisons,
            'note_set_slug': note_set_slug,
            'melodic_set_slug': melodic_set_slug,
            'extraction_method': 'crim_intervals_melodic',
            'end_parameter': False
        }
        
        # Save to cache
        data_dict = {'intervals': melodic_df}
        cache_manager.save_stage_cache('melodic_intervals', 'pkl', melodic_set_slug, piece_key, data_dict, metadata)
        print(f"  Saved melodic intervals to cache (shape: {melodic_df.shape})")
        
        return convert_melodic_intervals_to_list(melodic_df, piece_id, melodic_set_id, kind)
        
    except Exception as e:
        print(f"  Error extracting melodic intervals from {file_path}: {e}")
        import traceback
        traceback.print_exc()
        raise

def convert_melodic_intervals_to_list(melodic_df: pd.DataFrame, piece_id: int, melodic_set_id: int, kind: str) -> List[Dict]:
    """
    Convert melodic intervals DataFrame to list of dictionaries
    
    This function processes CRIM's melodic interval output:
    - For kind='quality': CRIM returns strings like 'P1', 'M3', 'm3', '-m2', etc.
    - For kind='diatonic': CRIM returns numbers like 1, 3, -2, 8, etc.
    
    We store the raw CRIM output and add analysis fields like direction and semitones.
    """
    intervals_list = []
    
    if melodic_df is None or melodic_df.empty:
        print(f"  Error: No valid interval dataframe found")
        return []
    
    print(f"  Converting melodic intervals DataFrame to list...")
    print(f"  DataFrame columns: {list(melodic_df.columns)}")
    print(f"  DataFrame index: {melodic_df.index.names if hasattr(melodic_df.index, 'names') else 'Single index'}")
    
    # Get voice columns (exclude metadata columns)
    metadata_cols = ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']
    voice_columns = [col for col in melodic_df.columns if col not in metadata_cols]
    
    print(f"  Voice columns found: {voice_columns}")
    
    # Iterate through each row (time point) of the DataFrame
    for idx, row in melodic_df.iterrows():
        # Extract timing information
        offset = idx
        measure = None
        beat = None
        
        # Check if we have multi-index or columns with timing info
        if isinstance(melodic_df.index, pd.MultiIndex):
            # Multi-index case (Offset, Measure, Beat)
            if len(idx) >= 1:
                offset = idx[0]
            if len(idx) >= 2:
                measure = idx[1]
            if len(idx) >= 3:
                beat = idx[2]
        else:
            # Single index, check for timing columns
            if 'Measure' in melodic_df.columns:
                measure = row.get('Measure')
            if 'Beat' in melodic_df.columns:
                beat = row.get('Beat')
            if 'Offset' in melodic_df.columns:
                offset = row.get('Offset')
        
        # Process each voice at this time point
        for voice_idx, voice_name in enumerate(voice_columns, 1):
            interval_value = melodic_df.loc[idx, voice_name]
            
            # Skip if no interval value
            if pd.isna(interval_value) or interval_value == '' or interval_value is None:
                continue
            
            # Parse interval information based on kind
            interval_semitones = None
            interval_type = None
            interval_quality = None
            
            try:
                if kind == 'diatonic':
                    # Diatonic intervals from CRIM are already in the correct format (e.g., "3", "-2", "8")
                    # We just store them as-is and determine direction
                    interval_type = str(interval_value)
                    
                    # Determine direction from the value
                    if isinstance(interval_value, (int, float)):
                        diatonic_number = int(interval_value)
                        if diatonic_number < 0:
                            interval_direction = "descending"
                        elif diatonic_number == 0 or abs(diatonic_number) == 1:
                            interval_direction = "unison"
                        else:
                            interval_direction = "ascending"
                    else:
                        # Handle string values
                        str_value = str(interval_value)
                        if str_value.startswith('-'):
                            interval_direction = "descending"
                        elif str_value in ['0', '1']:
                            interval_direction = "unison"
                        else:
                            interval_direction = "ascending"
                    
                    # For diatonic intervals, we don't convert to semitones since CRIM provides the raw diatonic number
                    interval_semitones = None
                
                elif kind == 'quality':
                    # Quality intervals from CRIM are already in the correct format (e.g., 'P1', 'm2', 'M3', '-m2')
                    # We just store them as-is and optionally convert to semitones for analysis
                    interval_type = str(interval_value)
                    
                    # Parse CRIM interval notation to semitones for analysis purposes
                    interval_semitones = parse_crim_interval_to_semitones(interval_value)
                    
                    # Determine direction from interval string
                    if str(interval_value).startswith('-'):
                        interval_direction = "descending"
                    elif str(interval_value) in ['P1', 'P8', 'P15']:  # Unisons and octaves
                        interval_direction = "unison"
                    else:
                        interval_direction = "ascending"
                
                else:
                    # Handle other formats or unknown types
                    interval_type = str(interval_value)
                    
            except Exception as e:
                print(f"    Warning: Could not parse interval '{interval_value}': {e}")
                interval_type = str(interval_value)
            
            # Create interval record
            interval_data = {
                'piece_id': piece_id,
                'melodic_interval_set_id': melodic_set_id,
                'voice': voice_idx,
                'onset': float(offset),
                'interval_type': interval_type,
                'voice_name': voice_name
            }
            
            intervals_list.append(interval_data)
    
    print(f"  Converted to {len(intervals_list)} melodic interval records")
    return intervals_list

def create_melodic_intervals_table():
    """Create a table for storing melodic intervals in the database"""
    db = PiecesDB()
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS melodic_intervals (
        interval_id INTEGER PRIMARY KEY AUTOINCREMENT,
        piece_id INTEGER NOT NULL,
        melodic_interval_set_id INTEGER NOT NULL,
        voice INTEGER NOT NULL,
        onset REAL NOT NULL,             -- Interval onset time
        interval_type TEXT,              -- CRIM raw output (P1, m2, M3 or 1, 2, 3)
        voice_name TEXT,                 -- Voice name
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (piece_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
        FOREIGN KEY (melodic_interval_set_id) REFERENCES melodic_interval_sets (set_id) ON DELETE CASCADE
    );
    
    CREATE INDEX IF NOT EXISTS idx_melodic_intervals_piece ON melodic_intervals(piece_id);
    CREATE INDEX IF NOT EXISTS idx_melodic_intervals_set ON melodic_intervals(melodic_interval_set_id);
    CREATE INDEX IF NOT EXISTS idx_melodic_intervals_voice ON melodic_intervals(voice);
    CREATE INDEX IF NOT EXISTS idx_melodic_intervals_onset ON melodic_intervals(onset);
    """
    
    try:
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.executescript(create_table_sql)
        conn.commit()
        conn.close()
        print("Melodic intervals table created successfully")
    except Exception as e:
        print(f"Error creating melodic intervals table: {e}")
        if 'conn' in locals():
            conn.close()
        raise

def insert_melodic_intervals_batch(intervals_list: List[Dict]) -> int:
    """Insert a batch of melodic intervals into the database"""
    if not intervals_list:
        return 0
    
    db = PiecesDB()
    
    insert_sql = """
    INSERT INTO melodic_intervals (
        piece_id, melodic_interval_set_id, voice, onset, interval_type, voice_name, note_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    values_list = []
    for interval in intervals_list:
        values = (
            interval.get('piece_id'),
            interval.get('melodic_interval_set_id'),
            interval.get('voice'),
            interval.get('onset'),
            interval.get('interval_type'),
            interval.get('voice_name'),
            interval.get('note_id')
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
        print(f"Error inserting melodic intervals: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return 0

def melodic_intervals_exist_for_piece_and_set(piece_id: int, melodic_set_id: int) -> bool:
    """Check if melodic intervals already exist for a piece and melodic interval set"""
    db = PiecesDB()
    
    try:
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM melodic_intervals 
            WHERE piece_id = ? AND melodic_interval_set_id = ?
        """, (piece_id, melodic_set_id))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        print(f"Error checking melodic intervals existence: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def ingest_melodic_intervals_for_all_pieces():
    """Main function to ingest melodic intervals for all pieces using all melodic interval sets"""
    
    # Check if crim_intervals is available before proceeding
    if not CRIM_INTERVALS_AVAILABLE:
        print("Cannot proceed without crim_intervals library.")
        return
    
    # Create the melodic intervals table if it doesn't exist
    print("Creating melodic intervals table...")
    create_melodic_intervals_table()
    
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
    
    # Get all melodic interval sets
    print("Retrieving all melodic interval sets...")
    melodic_sets = db.get_all_melodic_interval_sets()
    
    if not melodic_sets:
        print("No melodic interval sets found in database.")
        print("Please run core/db/init_db.py first to create parameter sets.")
        return
    
    print(f"Found {len(melodic_sets)} melodic interval sets:")
    for melodic_set in melodic_sets:
        print(f"  Set {melodic_set['set_id']}: {melodic_set['slug']} (kind={melodic_set['kind']}, note_set_id={melodic_set['note_set_id']})")
    
    # Get project root directory (two levels up from core/ingest/)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_root = os.path.join(project_root, 'data')
    
    total_combinations = len(pieces) * len(melodic_sets)
    processed_count = 0
    skipped_count = 0
    error_count = 0
    total_intervals = 0
    
    print(f"\n=== Processing {total_combinations} combinations (pieces × melodic sets) ===")
    
    # Process each melodic interval set
    for melodic_set in melodic_sets:
        melodic_set_id = melodic_set['set_id']
        melodic_slug = melodic_set['slug']
        kind = melodic_set['kind']
        note_set_id = melodic_set['note_set_id']
        
        # Get the corresponding note set to find combine_unisons value
        note_sets = db.get_all_note_sets()
        note_set = next((ns for ns in note_sets if ns['set_id'] == note_set_id), None)
        if not note_set:
            print(f"Error: Could not find note set with id {note_set_id}")
            continue
            
        combine_unisons = note_set['combine_unisons']
        note_set_slug = note_set['slug']
        
        print(f"\n--- Processing Melodic Interval Set {melodic_set_id}: {melodic_slug} ---")
        print(f"Kind: {kind}, Combine Unisons: {combine_unisons}")
        print(f"Using notes from set: {note_set_slug}")
        
        set_processed = 0
        set_skipped = 0
        set_errors = 0
        set_intervals = 0
        
        # Process each piece with this melodic interval set
        for i, piece in enumerate(pieces, 1):
            piece_id = piece['piece_id']
            piece_path = piece['path']
            piece_filename = piece['filename']
            
            print(f"Processing piece {i}: {piece_filename} (Set {melodic_set_id})")
            
            try:
                # Check if melodic intervals already exist for this piece and set
                if melodic_intervals_exist_for_piece_and_set(piece_id, melodic_set_id):
                    print(f"  Skipping - melodic intervals already exist for piece {piece_id} with set {melodic_set_id}")
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
                
                # Extract melodic intervals from the piece
                intervals_list = extract_melodic_intervals_from_piece(
                    full_file_path, piece_id, melodic_set_id, kind, combine_unisons, 
                    note_set_slug, melodic_slug
                )
                
                if not intervals_list:
                    print(f"  Warning: No melodic intervals extracted from {piece_filename}")
                    processed_count += 1  # Still count as processed
                    set_processed += 1
                    continue
                
                # Insert melodic intervals into database
                print(f"  Inserting {len(intervals_list)} melodic intervals into database...")
                success_count = insert_melodic_intervals_batch(intervals_list)
                
                if success_count == len(intervals_list):
                    print(f"  Successfully inserted {success_count} melodic intervals")
                    processed_count += 1
                    set_processed += 1
                    total_intervals += success_count
                    set_intervals += success_count
                else:
                    print(f"  Warning: Only {success_count}/{len(intervals_list)} melodic intervals inserted")
                    error_count += 1
                    set_errors += 1
                    
            except Exception as e:
                print(f"  Error processing piece {piece_id}: {e}")
                error_count += 1
                set_errors += 1
                continue
        
        # Print set summary
        print(f"\n--- Set {melodic_set_id} Summary ---")
        print(f"Successfully processed: {set_processed}")
        print(f"Skipped (already exists): {set_skipped}")
        print(f"Errors: {set_errors}")
        print(f"Intervals inserted: {set_intervals}")
    
    # Print overall summary
    print(f"\n============================================================")
    print(f"=== Overall Melodic Intervals Ingestion Summary ===")
    print(f"Total melodic interval sets: {len(melodic_sets)}")
    print(f"Total pieces: {len(pieces)}")
    print(f"Total combinations processed: {processed_count}")
    print(f"Total combinations skipped: {skipped_count}")
    print(f"Total errors: {error_count}")
    print(f"Total melodic intervals inserted: {total_intervals}")
    
    # Print cache statistics
    print(f"\n=== Cache Statistics ===")
    stats = cache_manager.get_cache_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Update note_id fields for newly inserted melodic intervals
    print(f"\n=== Updating note_id fields ===")
    try:
        updater = NoteIdUpdater()
        updated_count = updater.update_note_ids_batch_optimized('melodic_intervals')
        print(f"Updated {updated_count} melodic intervals with note_id references")
    except Exception as e:
        print(f"Error updating note_id fields: {e}")

if __name__ == "__main__":
    ingest_melodic_intervals_for_all_pieces()
