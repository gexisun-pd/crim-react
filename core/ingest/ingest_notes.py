import os
import sys
from typing import List, Dict, Optional
import pandas as pd

# Add the core directory to the path to import db module
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db.db import PiecesDB
from crim_cache_manager import cache_manager

# Import crim_intervals for note extraction
try:
    import crim_intervals
    from crim_intervals import CorpusBase
    # Try to import ImportedPiece from different locations
    try:
        from crim_intervals.main_objs import ImportedPiece
    except ImportError:
        try:
            from crim_intervals import ImportedPiece
        except ImportError:
            # We'll try to access it through the module directly
            ImportedPiece = None
    CRIM_INTERVALS_AVAILABLE = True
except ImportError:
    print("Error: crim_intervals library is required but not available.")
    print("Please install crim_intervals")
    CRIM_INTERVALS_AVAILABLE = False
    ImportedPiece = None

def extract_notes_from_piece(file_path: str, piece_id: int) -> Optional[List[Dict]]:
    """Extract notes from a piece using CRIM intervals library with caching"""
    if not CRIM_INTERVALS_AVAILABLE:
        raise ImportError("crim_intervals library is required for note extraction")
    
    filename = os.path.basename(file_path)
    piece_key = cache_manager._get_piece_key(filename)
    
    print(f"  Processing piece: {piece_key}")
    
    # Check cache first
    notes_df = cache_manager.load_dataframe(piece_key, 'notes')
    durations_df = cache_manager.load_dataframe(piece_key, 'durations')
    detail_df = cache_manager.load_dataframe(piece_key, 'detail_index')
    
    if notes_df is not None and durations_df is not None and detail_df is not None:
        print(f"  Using cached DataFrames for {piece_key}")
        return convert_notes_with_details_to_list(detail_df, durations_df, piece_id)
    
    try:
        print(f"  Creating corpus and extracting notes...")
        
        # Create a corpus with just this piece
        corpus = CorpusBase([file_path])
        
        # Access the piece from corpus.scores
        if not hasattr(corpus, 'scores') or len(corpus.scores) == 0:
            print(f"  Error: No scores found in corpus")
            return []
        
        piece = corpus.scores[0]
        
        print(f"  Extracting notes using CRIM intervals...")
        
        # Get the basic notes DataFrame
        notes_df = piece.notes()
        
        if notes_df.empty:
            print(f"  Warning: No notes found in {file_path}")
            return []
        
        print(f"  Getting durations...")
        # Get durations DataFrame
        durations_df = piece.durations()
        
        print(f"  Adding measure and beat information using detailIndex...")
        # Use detailIndex to get measure and beat information
        detail_df = piece.detailIndex(notes_df, measure=True, beat=True, offset=True)
        
        print(f"  Notes DataFrame shape: {notes_df.shape}")
        print(f"  Notes with details shape: {detail_df.shape}")
        print(f"  Durations DataFrame shape: {durations_df.shape}")
        
        # Save to cache with metadata
        metadata = {
            'file_path': file_path,
            'piece_id': piece_id,
            'extraction_method': 'crim_intervals'
        }
        
        cache_manager.save_dataframe(piece_key, 'notes', notes_df, metadata)
        cache_manager.save_dataframe(piece_key, 'durations', durations_df, metadata)
        cache_manager.save_dataframe(piece_key, 'detail_index', detail_df, metadata)
        
        print(f"  Saved DataFrames to cache for {piece_key}")
        
        return convert_notes_with_details_to_list(detail_df, durations_df, piece_id)
        
    except Exception as e:
        print(f"  Error extracting notes from {file_path}: {e}")
        import traceback
        traceback.print_exc()
        raise

def convert_notes_with_details_to_list(notes_df, durations_df, piece_id: int) -> List[Dict]:
    """Convert notes DataFrame with detail index to list of dictionaries
    
    Args:
        notes_df: DataFrame from piece.detailIndex(piece.notes(), measure=True, beat=True, offset=True)
        durations_df: DataFrame from piece.durations()
        piece_id: ID of the piece in the database
    
    Returns:
        List of note dictionaries for database insertion
    """
    notes_list = []
    
    print(f"  Converting notes DataFrame to list...")
    print(f"  Notes DataFrame columns: {list(notes_df.columns)}")
    print(f"  Notes DataFrame index: {notes_df.index.names if hasattr(notes_df.index, 'names') else 'Single index'}")
    
    # Get voice columns (exclude metadata columns)
    metadata_cols = ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']
    voice_columns = [col for col in notes_df.columns if col not in metadata_cols]
    
    print(f"  Voice columns found: {voice_columns}")
    
    # Iterate through each row (time point)
    for idx, row in notes_df.iterrows():
        # Extract timing information
        offset = idx
        measure = None
        beat = None
        
        # Check if we have multi-index or columns with timing info
        if isinstance(notes_df.index, pd.MultiIndex):
            # Multi-index case (Offset, Measure, Beat)
            if len(idx) >= 1:
                offset = idx[0]
            if len(idx) >= 2:
                measure = idx[1]
            if len(idx) >= 3:
                beat = idx[2]
        else:
            # Single index, check for timing columns
            if 'Measure' in notes_df.columns:
                measure = row.get('Measure')
            if 'Beat' in notes_df.columns:
                beat = row.get('Beat')
            if 'Offset' in notes_df.columns:
                offset = row.get('Offset')
        
        # Get duration for this offset
        duration = 0.0
        try:
            if offset in durations_df.index:
                duration_row = durations_df.loc[offset]
                # Get the first non-null duration value from any voice
                if isinstance(duration_row, pd.Series):
                    for voice_col in voice_columns:
                        if voice_col in duration_row and pd.notna(duration_row[voice_col]):
                            duration = float(duration_row[voice_col])
                            break
                elif isinstance(duration_row, (int, float)):
                    duration = float(duration_row)
        except Exception as e:
            print(f"    Warning: Could not get duration for offset {offset}: {e}")
            duration = 0.0
        
        # Process each voice at this time point
        for voice_idx, voice_name in enumerate(voice_columns, 1):
            note_value = row[voice_name]
            
            # Skip NaN, empty, or None values
            if pd.isna(note_value) or note_value == '' or note_value is None:
                continue
            
            # Parse note information
            note_type = "Rest" if str(note_value).strip() == "Rest" else "Note"
            
            # Initialize note attributes
            pitch = None
            name = str(note_value)
            step = None
            octave = None
            alter = 0
            
            if note_type == "Note" and note_value != "Rest":
                # Try to parse the note name (e.g., "A4", "C#5", "Bb3")
                try:
                    note_str = str(note_value).strip()
                    if len(note_str) >= 2:
                        # Extract step (note name)
                        step = note_str[0].upper()
                        
                        # Extract alterations
                        alter = 0
                        if '#' in note_str:
                            alter = 1
                        elif 'b' in note_str or '♭' in note_str:
                            alter = -1
                        
                        # Extract octave
                        octave_str = ''.join(filter(str.isdigit, note_str))
                        octave = int(octave_str) if octave_str else None
                        
                        # Convert to MIDI pitch if we have all components
                        if step and octave is not None:
                            step_to_midi = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
                            base_pitch = step_to_midi.get(step, 0)
                            pitch = (octave + 1) * 12 + base_pitch + alter
                except Exception as e:
                    print(f"    Warning: Could not parse note '{note_value}': {e}")
            
            # Create note record
            note_data = {
                'piece_id': piece_id,
                'voice': voice_idx,
                'voice_name': voice_name,  # Store the voice name from CRIM (e.g., "Cantus", "Altus")
                'onset': float(offset),
                'duration': duration,
                'offset': float(offset) + float(duration),
                'measure': int(measure) if measure is not None and pd.notna(measure) else None,
                'beat': float(beat) if beat is not None and pd.notna(beat) else None,
                'pitch': pitch,
                'name': name,
                'step': step,
                'octave': octave,
                'alter': alter,
                'type': note_type,
                'staff': voice_idx,
                'tie': None  # We'll implement tie detection later if needed
            }
            notes_list.append(note_data)
    
    print(f"  Converted to {len(notes_list)} individual note records")
    return notes_list


def parse_note_name(note_name: str) -> tuple:
    """Parse a note name like 'A4', 'C#5', 'Bb3' into pitch components
    
    Returns: (midi_pitch, step, octave, alter)
    """
    import re
    
    if not note_name or note_name == 'Rest':
        return None, None, None, None
    
    # Pattern to match note names: letter + optional accidental + octave
    pattern = r'^([A-G])([#b]?)(\d+)$'
    match = re.match(pattern, note_name)
    
    if not match:
        return None, note_name[0] if note_name else None, None, None
    
    step = match.group(1)
    accidental = match.group(2)
    octave = int(match.group(3))
    
    # Convert accidental to alter value
    if accidental == '#':
        alter = 1
    elif accidental == 'b':
        alter = -1
    else:
        alter = 0
    
    # Calculate MIDI pitch
    # C4 = 60, C0 = 12
    step_to_semitone = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    base_pitch = (octave + 1) * 12 + step_to_semitone[step]
    midi_pitch = base_pitch + alter
    
    return midi_pitch, step, octave, alter

def ingest_notes_for_all_pieces():
    """Main function to ingest notes for all pieces in the database"""
    
    # Check if crim_intervals is available before proceeding
    if not CRIM_INTERVALS_AVAILABLE:
        print("Cannot proceed without crim_intervals library.")
        return
    
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
    total_notes = 0
    
    # Process each piece
    for piece in pieces:
        piece_id = piece['piece_id']
        piece_path = piece['path']
        piece_filename = piece['filename']
        
        print(f"\nProcessing piece {piece_id}: {piece_filename}")
        
        try:
            # Check if notes already exist for this piece
            if db.notes_exist_for_piece(piece_id):
                print(f"  Skipping - notes already exist for piece {piece_id}")
                skipped_count += 1
                continue
            
            # Construct full file path
            full_file_path = os.path.join(data_root, piece_path)
            
            if not os.path.exists(full_file_path):
                print(f"  Error: File not found: {full_file_path}")
                error_count += 1
                continue
            
            # Extract notes from the piece
            notes_list = extract_notes_from_piece(full_file_path, piece_id)
            
            if not notes_list:
                print(f"  Warning: No notes extracted from {piece_filename}")
                processed_count += 1  # Still count as processed
                continue
            
            # Insert notes into database
            print(f"  Inserting {len(notes_list)} notes into database...")
            success_count = db.insert_notes_batch(notes_list)
            
            if success_count == len(notes_list):
                print(f"  Successfully inserted {success_count} notes")
                processed_count += 1
                total_notes += success_count
            else:
                print(f"  Warning: Only {success_count}/{len(notes_list)} notes inserted")
                error_count += 1
                
        except Exception as e:
            print(f"  Error processing piece {piece_id}: {e}")
            error_count += 1
            continue
    
    # Print summary
    print(f"\n=== Notes Ingestion Summary ===")
    print(f"Total pieces found: {len(pieces)}")
    print(f"Successfully processed: {processed_count}")
    print(f"Skipped (already exists): {skipped_count}")
    print(f"Errors: {error_count}")
    print(f"Total notes inserted: {total_notes}")

if __name__ == "__main__":
    ingest_notes_for_all_pieces()
