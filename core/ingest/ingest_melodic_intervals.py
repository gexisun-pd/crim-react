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

def extract_melodic_intervals_from_piece(file_path: str, piece_id: int) -> Optional[List[Dict]]:
    """Extract melodic intervals from a piece using cached CRIM DataFrames"""
    if not CRIM_INTERVALS_AVAILABLE:
        raise ImportError("crim_intervals library is required for melodic intervals extraction")
    
    filename = os.path.basename(file_path)
    piece_key = cache_manager._get_piece_key(filename)
    
    print(f"  Processing melodic intervals for piece: {piece_key}")
    
    # Try to load cached DataFrames first
    notes_df = cache_manager.load_dataframe(piece_key, 'notes')
    durations_df = cache_manager.load_dataframe(piece_key, 'durations')
    detail_df = cache_manager.load_dataframe(piece_key, 'detail_index')
    
    if notes_df is None or durations_df is None or detail_df is None:
        print(f"  Error: Required cached DataFrames not found for {piece_key}")
        print(f"  Please run ingest_notes.py first to cache the DataFrames")
        return []
    
    print(f"  Using cached DataFrames for melodic intervals extraction")
    
    # Check if melodic intervals are already cached
    melodic_intervals_df = cache_manager.load_dataframe(piece_key, 'melodic_intervals')
    
    if melodic_intervals_df is not None:
        print(f"  Using cached melodic intervals DataFrame")
        return convert_melodic_intervals_to_list(melodic_intervals_df, piece_id)
    
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
        
        # Extract melodic intervals using the piece object
        # According to CRIM documentation, melodic() should be called without parameters
        # or with specific parameters. Let's try without parameters first
        try:
            melodic_intervals_df = piece.melodic()
        except Exception as e:
            print(f"  Error with piece.melodic(): {e}")
            print(f"  Trying with notes_df parameter...")
            # If that fails, try with the original approach but check the notes_df format
            try:
                # Make sure the notes_df is in the right format for CRIM
                # Reset index to make sure it's numeric and continuous
                notes_df_reset = notes_df.reset_index(drop=True)
                melodic_intervals_df = piece.melodic(notes_df_reset)
            except Exception as e2:
                print(f"  Error with piece.melodic(notes_df_reset): {e2}")
                print(f"  Trying direct call to piece.melodic() from fresh corpus...")
                # Try getting melodic intervals directly without cached dataframes
                melodic_intervals_df = piece.melodic()
        
        if melodic_intervals_df.empty:
            print(f"  Warning: No melodic intervals found in {file_path}")
            return []
        
        print(f"  Melodic intervals DataFrame shape: {melodic_intervals_df.shape}")
        print(f"  Melodic intervals columns: {list(melodic_intervals_df.columns)}")
        
        # Add detailed timing information using detailIndex
        melodic_intervals_with_detail = piece.detailIndex(melodic_intervals_df, measure=True, beat=True, offset=True)
        
        # Save to cache with metadata
        metadata = {
            'file_path': file_path,
            'piece_id': piece_id,
            'extraction_method': 'crim_intervals_melodic',
            'based_on_notes_cache': True
        }
        
        cache_manager.save_dataframe(piece_key, 'melodic_intervals', melodic_intervals_df, metadata)
        cache_manager.save_dataframe(piece_key, 'melodic_intervals_detail', melodic_intervals_with_detail, metadata)
        
        print(f"  Saved melodic intervals DataFrames to cache for {piece_key}")
        
        return convert_melodic_intervals_to_list(melodic_intervals_with_detail, piece_id)
        
    except Exception as e:
        print(f"  Error extracting melodic intervals from {file_path}: {e}")
        import traceback
        traceback.print_exc()
        raise

def convert_melodic_intervals_to_list(intervals_df, piece_id: int) -> List[Dict]:
    """Convert melodic intervals DataFrame to list of dictionaries"""
    intervals_list = []
    
    print(f"  Converting melodic intervals DataFrame to list...")
    print(f"  Intervals DataFrame columns: {list(intervals_df.columns)}")
    print(f"  Intervals DataFrame index: {intervals_df.index.names if hasattr(intervals_df.index, 'names') else 'Single index'}")
    
    # Get voice columns (exclude metadata columns)
    metadata_cols = ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']
    voice_columns = [col for col in intervals_df.columns if col not in metadata_cols]
    
    print(f"  Voice columns found: {voice_columns}")
    
    # Iterate through each row (time point)
    for idx, row in intervals_df.iterrows():
        # Extract timing information
        offset = idx
        measure = None
        beat = None
        
        # Check if we have multi-index or columns with timing info
        if isinstance(intervals_df.index, pd.MultiIndex):
            # Multi-index case (Offset, Measure, Beat)
            if len(idx) >= 1:
                offset = idx[0]
            if len(idx) >= 2:
                measure = idx[1]
            if len(idx) >= 3:
                beat = idx[2]
        else:
            # Single index, check for timing columns
            if 'Measure' in intervals_df.columns:
                measure = row.get('Measure')
            if 'Beat' in intervals_df.columns:
                beat = row.get('Beat')
            if 'Offset' in intervals_df.columns:
                offset = row.get('Offset')
        
        # Process each voice at this time point
        for voice_idx, voice_name in enumerate(voice_columns, 1):
            interval_value = row[voice_name]
            
            # Skip NaN, empty, or None values
            if pd.isna(interval_value) or interval_value == '' or interval_value is None:
                continue
            
            # Parse interval information
            # CRIM melodic intervals are typically numeric (semitones)
            interval_semitones = None
            interval_type = None
            interval_direction = None
            interval_quality = None
            
            try:
                if isinstance(interval_value, (int, float)):
                    interval_semitones = float(interval_value)
                    
                    # Determine direction
                    if interval_semitones > 0:
                        interval_direction = "ascending"
                    elif interval_semitones < 0:
                        interval_direction = "descending"
                    else:
                        interval_direction = "unison"
                    
                    # Convert to interval type (rough approximation)
                    abs_semitones = abs(interval_semitones)
                    interval_names = {
                        0: "unison",
                        1: "minor 2nd", 2: "major 2nd",
                        3: "minor 3rd", 4: "major 3rd",
                        5: "perfect 4th", 6: "tritone", 7: "perfect 5th",
                        8: "minor 6th", 9: "major 6th",
                        10: "minor 7th", 11: "major 7th",
                        12: "octave"
                    }
                    
                    if abs_semitones in interval_names:
                        interval_type = interval_names[abs_semitones]
                    elif abs_semitones > 12:
                        # Compound intervals
                        octaves = abs_semitones // 12
                        remainder = abs_semitones % 12
                        if remainder in interval_names:
                            interval_type = f"{interval_names[remainder]} + {octaves} octave(s)"
                        else:
                            interval_type = f"{abs_semitones} semitones"
                    else:
                        interval_type = f"{abs_semitones} semitones"
                
                elif isinstance(interval_value, str):
                    # If it's a string, try to parse it
                    interval_type = str(interval_value)
                    try:
                        interval_semitones = float(interval_value)
                    except ValueError:
                        interval_semitones = None
                
            except Exception as e:
                print(f"    Warning: Could not parse interval '{interval_value}': {e}")
                interval_type = str(interval_value)
            
            # Create interval record
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
        voice INTEGER NOT NULL,
        onset REAL NOT NULL,
        measure INTEGER,
        beat REAL,
        interval_semitones REAL,
        interval_type TEXT,
        interval_direction TEXT,
        interval_quality TEXT,
        voice_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (piece_id) REFERENCES pieces (piece_id)
    );
    
    CREATE INDEX IF NOT EXISTS idx_melodic_intervals_piece ON melodic_intervals(piece_id);
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
        piece_id, voice, onset, measure, beat, interval_semitones,
        interval_type, interval_direction, interval_quality, voice_name
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    values_list = []
    for interval in intervals_list:
        values = (
            interval.get('piece_id'),
            interval.get('voice'),
            interval.get('onset'),
            interval.get('measure'),
            interval.get('beat'),
            interval.get('interval_semitones'),
            interval.get('interval_type'),
            interval.get('interval_direction'),
            interval.get('interval_quality'),
            interval.get('voice_name')
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
