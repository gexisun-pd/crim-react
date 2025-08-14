import os
import sys
from typing import List, Dict, Optional
import pandas as pd

# Add the core directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db.db import PiecesDB
from crim_cache_manager import cache_manager

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

def extract_melodic_intervals_from_piece(file_path: str, piece_id: int) -> Optional[List[Dict]]:
    """Extract melodic intervals from a piece using cached CRIM DataFrames"""
    if not CRIM_INTERVALS_AVAILABLE:
        raise ImportError("crim_intervals library is required for melodic intervals extraction")
    
    filename = os.path.basename(file_path)
    piece_key = cache_manager._get_piece_key(filename)
    
    print(f"  Processing melodic intervals for piece: {piece_key}")
    
    # Try to load cached DataFrames first
    notes_df = cache_manager.load_dataframe(piece_key, 'notes')
    
    if notes_df is None:
        print(f"  Error: Required cached DataFrames not found for {piece_key}")
        print(f"  Please run ingest_notes.py first to cache the DataFrames")
        return []
    
    print(f"  Using cached DataFrames for melodic intervals extraction")
    
    # Check if melodic intervals are already cached (check all types)
    interval_types = ['quality', 'diatonic', 'chromatic', 'zerobased']
    cached_intervals = {}
    all_cached = True
    
    for interval_type in interval_types:
        cache_key = f'melodic_intervals_{interval_type}'
        cached_df = cache_manager.load_dataframe(piece_key, cache_key)
        if cached_df is not None:
            cached_intervals[interval_type] = cached_df
        else:
            all_cached = False
    
    if all_cached and cached_intervals:
        print(f"  Using cached melodic intervals DataFrames (all types)")
        return convert_melodic_intervals_to_list(cached_intervals, piece_id)
    
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
        
        # Debug: Check the structure of notes_df
        print(f"  Notes DataFrame columns: {list(notes_df.columns)}")
        print(f"  Notes DataFrame index: {notes_df.index[:5]}")
        print(f"  Notes DataFrame shape: {notes_df.shape}")
        
        # Extract melodic intervals using different kinds
        # According to CRIM documentation, we can extract different types of intervals
        interval_types = {
            'quality': {'kind': 'q', 'description': 'Diatonic with quality (P8, M3, m3)'},
            'diatonic': {'kind': 'd', 'description': 'Diatonic without quality (8, 3)'},
            'chromatic': {'kind': 'c', 'description': 'Chromatic in semitones (12, 6, 0)'},
            'zerobased': {'kind': 'z', 'description': 'Zero-based diatonic (7, -4, 2)'}
        }
        
        melodic_intervals_dataframes = {}
        
        for interval_name, config in interval_types.items():
            print(f"  Extracting {interval_name} intervals (kind='{config['kind']}')...")
            try:
                # Use end=False to associate intervals with the first note of the pair
                melodic_df = piece.melodic(kind=config['kind'], end=False)
                melodic_intervals_dataframes[interval_name] = melodic_df
                print(f"    {interval_name} intervals shape: {melodic_df.shape}")
            except Exception as e:
                print(f"    Error extracting {interval_name} intervals: {e}")
                melodic_intervals_dataframes[interval_name] = None
        
        # Use quality intervals as the primary one for conversion
        melodic_intervals_df = melodic_intervals_dataframes.get('quality')
        if melodic_intervals_df is None or melodic_intervals_df.empty:
            print(f"  Warning: No melodic intervals found in {file_path}")
            return []
        
        print(f"  Melodic intervals DataFrame shape: {melodic_intervals_df.shape}")
        print(f"  Melodic intervals columns: {list(melodic_intervals_df.columns)}")
        
        # Save all types of melodic intervals to cache with metadata
        metadata = {
            'file_path': file_path,
            'piece_id': piece_id,
            'extraction_method': 'crim_intervals_melodic_all_types',
            'based_on_notes_cache': True,
            'end_parameter': False
        }
        
        # Save each type of melodic intervals to cache
        for interval_name, df in melodic_intervals_dataframes.items():
            if df is not None and not df.empty:
                cache_key = f'melodic_intervals_{interval_name}'
                cache_manager.save_dataframe(piece_key, cache_key, df, metadata)
                print(f"    Saved {interval_name} intervals to cache (shape: {df.shape})")
        
        print(f"  Saved all melodic intervals DataFrames to cache for {piece_key}")
        
        return convert_melodic_intervals_to_list(melodic_intervals_dataframes, piece_id)
        
    except Exception as e:
        print(f"  Error extracting melodic intervals from {file_path}: {e}")
        import traceback
        traceback.print_exc()
        raise

def convert_melodic_intervals_to_list(intervals_dataframes: Dict, piece_id: int) -> List[Dict]:
    """Convert multiple melodic intervals DataFrames to list of dictionaries"""
    intervals_list = []
    
    # Use quality intervals as the primary reference for timing and structure
    primary_df = intervals_dataframes.get('quality')
    if primary_df is None or primary_df.empty:
        print(f"  Warning: No quality intervals found, trying other types...")
        for interval_type, df in intervals_dataframes.items():
            if df is not None and not df.empty:
                primary_df = df
                break
    
    if primary_df is None or primary_df.empty:
        print(f"  Error: No valid interval dataframes found")
        return []
    
    print(f"  Converting melodic intervals DataFrames to list...")
    print(f"  Primary DataFrame columns: {list(primary_df.columns)}")
    print(f"  Primary DataFrame index: {primary_df.index.names if hasattr(primary_df.index, 'names') else 'Single index'}")
    
    # Get voice columns (exclude metadata columns)
    metadata_cols = ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']
    voice_columns = [col for col in primary_df.columns if col not in metadata_cols]
    
    print(f"  Voice columns found: {voice_columns}")
    
    # Iterate through each row (time point) of the primary DataFrame
    for idx, row in primary_df.iterrows():
        # Extract timing information
        offset = idx
        measure = None
        beat = None
        
        # Check if we have multi-index or columns with timing info
        if isinstance(primary_df.index, pd.MultiIndex):
            # Multi-index case (Offset, Measure, Beat)
            if len(idx) >= 1:
                offset = idx[0]
            if len(idx) >= 2:
                measure = idx[1]
            if len(idx) >= 3:
                beat = idx[2]
        else:
            # Single index, check for timing columns
            if 'Measure' in primary_df.columns:
                measure = row.get('Measure')
            if 'Beat' in primary_df.columns:
                beat = row.get('Beat')
            if 'Offset' in primary_df.columns:
                offset = row.get('Offset')
        
        # Process each voice at this time point
        for voice_idx, voice_name in enumerate(voice_columns, 1):
            # Check if any of the interval types have a non-null value for this voice at this time
            has_interval = False
            interval_values = {}
            
            # Collect interval values from all types
            for interval_type, df in intervals_dataframes.items():
                if df is not None and not df.empty and idx in df.index and voice_name in df.columns:
                    interval_value = df.loc[idx, voice_name]
                    if not pd.isna(interval_value) and interval_value != '' and interval_value is not None:
                        interval_values[interval_type] = interval_value
                        has_interval = True
            
            # Skip if no intervals found for this voice at this time
            if not has_interval:
                continue
            
            # Parse interval information from quality intervals (preferred) or chromatic as fallback
            primary_interval = interval_values.get('quality') or interval_values.get('chromatic')
            interval_semitones = None
            interval_type = None
            interval_direction = None
            interval_quality = None
            
            try:
                if isinstance(primary_interval, (int, float)):
                    # Numeric format (semitones) - from chromatic
                    interval_semitones = float(primary_interval)
                    interval_type = f"{interval_semitones} semitones"
                    
                    # Determine direction
                    if interval_semitones > 0:
                        interval_direction = "ascending"
                    elif interval_semitones < 0:
                        interval_direction = "descending"
                    else:
                        interval_direction = "unison"
                
                elif isinstance(primary_interval, str) and primary_interval not in ['Rest', 'NaN', '']:
                    # String format (like 'P1', 'm2', 'M3', '-m2') - from quality
                    interval_type = str(primary_interval)
                    
                    # Parse CRIM interval notation
                    interval_semitones = parse_crim_interval_to_semitones(primary_interval)
                    
                    # Determine direction from interval string
                    if primary_interval.startswith('-'):
                        interval_direction = "descending"
                    elif primary_interval in ['P1', 'P8', 'P15']:  # Unisons and octaves
                        interval_direction = "unison"
                    else:
                        interval_direction = "ascending"
                
                else:
                    # Handle Rest, NaN, or other special values
                    interval_type = str(primary_interval)
                    interval_semitones = None
                    interval_direction = None
                
            except Exception as e:
                print(f"    Warning: Could not parse interval '{primary_interval}': {e}")
                interval_type = str(primary_interval)
            
            # Create interval record with all interval types
            interval_data = {
                'piece_id': piece_id,
                'voice': voice_idx,
                'onset': float(offset),
                'measure': int(measure) if measure is not None and pd.notna(measure) else None,
                'beat': float(beat) if beat is not None and pd.notna(beat) else None,
                'interval_semitones': interval_semitones,
                'interval_type': interval_type,
                'interval_direction': interval_direction,
                'interval_quality': interval_quality,
                'voice_name': voice_name,
                'note_id': None,  # Simplified - no note matching for now
                'next_note_id': None,  # Simplified - no note matching for now
                
                # Add all interval types as separate fields
                'interval_quality_notation': interval_values.get('quality'),
                'interval_diatonic_notation': interval_values.get('diatonic'),
                'interval_chromatic_notation': interval_values.get('chromatic'),
                'interval_zerobased_notation': interval_values.get('zerobased')
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
        note_id INTEGER,                 -- Associated note_id (start note) - simplified, set to NULL for now
        next_note_id INTEGER,            -- Associated note_id (end note) - simplified, set to NULL for now
        voice INTEGER NOT NULL,
        onset REAL NOT NULL,             -- Interval onset time
        measure INTEGER,
        beat REAL,
        interval_semitones REAL,         -- Interval in semitones (from chromatic or parsed from quality)
        interval_type TEXT,              -- Primary interval type description
        interval_direction TEXT,         -- Interval direction: "ascending", "descending", "unison"
        interval_quality TEXT,           -- Interval quality
        voice_name TEXT,                 -- Voice name
        
        -- CRIM interval notations for all types
        interval_quality_notation TEXT,     -- Diatonic with quality (P8, M3, m3)
        interval_diatonic_notation TEXT,    -- Diatonic without quality (8, 3)
        interval_chromatic_notation TEXT,   -- Chromatic in semitones (12, 6, 0)
        interval_zerobased_notation TEXT,   -- Zero-based diatonic (7, -4, 2)
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (piece_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
        FOREIGN KEY (note_id) REFERENCES notes (note_id) ON DELETE SET NULL,
        FOREIGN KEY (next_note_id) REFERENCES notes (note_id) ON DELETE SET NULL
    );
    
    CREATE INDEX IF NOT EXISTS idx_melodic_intervals_piece ON melodic_intervals(piece_id);
    CREATE INDEX IF NOT EXISTS idx_melodic_intervals_voice ON melodic_intervals(voice);
    CREATE INDEX IF NOT EXISTS idx_melodic_intervals_onset ON melodic_intervals(onset);
    CREATE INDEX IF NOT EXISTS idx_melodic_intervals_note ON melodic_intervals(note_id);
    CREATE INDEX IF NOT EXISTS idx_melodic_intervals_next_note ON melodic_intervals(next_note_id);
    CREATE INDEX IF NOT EXISTS idx_melodic_intervals_semitones ON melodic_intervals(interval_semitones);
    CREATE INDEX IF NOT EXISTS idx_melodic_intervals_direction ON melodic_intervals(interval_direction);
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
        piece_id, note_id, next_note_id, voice, onset, measure, beat, 
        interval_semitones, interval_type, interval_direction, interval_quality, voice_name,
        interval_quality_notation, interval_diatonic_notation, 
        interval_chromatic_notation, interval_zerobased_notation
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    values_list = []
    for interval in intervals_list:
        values = (
            interval.get('piece_id'),
            interval.get('note_id'),
            interval.get('next_note_id'),
            interval.get('voice'),
            interval.get('onset'),
            interval.get('measure'),
            interval.get('beat'),
            interval.get('interval_semitones'),
            interval.get('interval_type'),
            interval.get('interval_direction'),
            interval.get('interval_quality'),
            interval.get('voice_name'),
            interval.get('interval_quality_notation'),
            interval.get('interval_diatonic_notation'),
            interval.get('interval_chromatic_notation'),
            interval.get('interval_zerobased_notation')
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

def melodic_intervals_exist_for_piece(piece_id: int) -> bool:
    """Check if melodic intervals already exist for a piece"""
    db = PiecesDB()
    
    try:
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM melodic_intervals WHERE piece_id = ?", (piece_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        print(f"Error checking melodic intervals existence: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def ingest_melodic_intervals_for_all_pieces():
    """Main function to ingest melodic intervals for all pieces in the database"""
    
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
    
    # Get project root directory (two levels up from core/ingest/)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_root = os.path.join(project_root, 'data')
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    total_intervals = 0
    
    # Process each piece
    for piece in pieces:
        piece_id = piece['piece_id']
        piece_path = piece['path']
        piece_filename = piece['filename']
        
        print(f"\nProcessing melodic intervals for piece {piece_id}: {piece_filename}")
        
        try:
            # Check if melodic intervals already exist for this piece
            if melodic_intervals_exist_for_piece(piece_id):
                print(f"  Skipping - melodic intervals already exist for piece {piece_id}")
                skipped_count += 1
                continue
            
            # Construct full file path
            full_file_path = os.path.join(data_root, piece_path)
            
            if not os.path.exists(full_file_path):
                print(f"  Error: File not found: {full_file_path}")
                error_count += 1
                continue
            
            # Extract melodic intervals from the piece
            intervals_list = extract_melodic_intervals_from_piece(full_file_path, piece_id)
            
            if not intervals_list:
                print(f"  Warning: No melodic intervals extracted from {piece_filename}")
                processed_count += 1  # Still count as processed
                continue
            
            # Insert melodic intervals into database
            print(f"  Inserting {len(intervals_list)} melodic intervals into database...")
            success_count = insert_melodic_intervals_batch(intervals_list)
            
            if success_count == len(intervals_list):
                print(f"  Successfully inserted {success_count} melodic intervals")
                processed_count += 1
                total_intervals += success_count
            else:
                print(f"  Warning: Only {success_count}/{len(intervals_list)} melodic intervals inserted")
                error_count += 1
                
        except Exception as e:
            print(f"  Error processing piece {piece_id}: {e}")
            error_count += 1
            continue
    
    # Print summary
    print(f"\n=== Melodic Intervals Ingestion Summary ===")
    print(f"Total pieces found: {len(pieces)}")
    print(f"Successfully processed: {processed_count}")
    print(f"Skipped (already exists): {skipped_count}")
    print(f"Errors: {error_count}")
    print(f"Total melodic intervals inserted: {total_intervals}")
    
    # Print cache statistics
    print(f"\n=== Cache Statistics ===")
    stats = cache_manager.get_cache_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    ingest_melodic_intervals_for_all_pieces()
