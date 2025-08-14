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
    """Convert notes DataFrame with detail index to list of dictionaries"""
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
                        elif 'b' in note_str:
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
                'onset': float(offset),
                'duration': duration,
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
    """Convert notes DataFrame and durations DataFrame to list of dictionaries"""
    notes_list = []
    
    # Get column names that represent voice parts (exclude measure, beat, offset columns)
    metadata_cols = ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']
    voice_columns = [col for col in notes_df.columns if col not in metadata_cols]
    
    print(f"  Voice columns found: {voice_columns}")
    
    for index, row in notes_df.iterrows():
        # Extract measure, beat, and offset information
        measure = None
        beat = None
        offset = index
        
        # Check if we have measure/beat information in the DataFrame
        if 'Measure' in notes_df.columns:
            measure = row.get('Measure')
        if 'Beat' in notes_df.columns:
            beat = row.get('Beat')
        if 'Offset' in notes_df.columns:
            offset = row.get('Offset')
        elif isinstance(notes_df.index, pd.MultiIndex):
            # Handle multi-index case
            if 'Offset' in notes_df.index.names:
                offset = index[notes_df.index.names.index('Offset')]
        
        # Get duration for this offset from durations_df
        duration = None
        if offset in durations_df.index:
            # Find the duration at this offset for any voice
            duration_row = durations_df.loc[offset]
            # Get the first non-null duration value
            if isinstance(duration_row, pd.Series):
                for voice_col in voice_columns:
                    if voice_col in duration_row and pd.notna(duration_row[voice_col]):
                        duration = float(duration_row[voice_col])
                        break
        
        # Process each voice part
        for voice_idx, voice_name in enumerate(voice_columns, 1):
            note_value = row[voice_name]
            
            # Skip NaN values and empty cells
            if pd.isna(note_value) or note_value == '':
                continue
            
            # Parse note information
            note_type = "Rest" if str(note_value).strip() == "Rest" else "Note"
            
            # Extract pitch information if it's a note
            pitch = None
            name = None
            step = None
            octave = None
            alter = None
            
            if note_type == "Note" and str(note_value) != "Rest":
                try:
                    # Parse note name using our helper function
                    pitch, step, octave, alter = parse_note_name(str(note_value).strip())
                    name = str(note_value).strip()
                except Exception:
                    # If parsing fails, just store the original value
                    name = str(note_value)
            else:
                name = "Rest"
            
            note_data = {
                'piece_id': piece_id,
                'voice': voice_idx,  # Use numeric voice index
                'onset': float(offset) if offset is not None else 0.0,
                'duration': duration if duration is not None else 1.0,  # Default to 1.0 if no duration found
                'measure': int(measure) if measure is not None and pd.notna(measure) else None,
                'beat': float(beat) if beat is not None and pd.notna(beat) else None,
                'pitch': pitch,
                'name': name,
                'step': step,
                'octave': octave,
                'alter': alter,
                'type': note_type,
                'staff': voice_idx,  # Assume staff equals voice
                'tie': None  # Not available in basic notes()
            }
            
            notes_list.append(note_data)
    
    return notes_list

def convert_notes_df_to_list_with_detail(notes_df, piece_id: int) -> List[Dict]:
    """Convert notes DataFrame with detailIndex to list of dictionaries"""
    notes_list = []
    
    # Get column names that represent voice parts (exclude measure, beat, offset columns)
    voice_columns = [col for col in notes_df.columns if col not in ['Measure', 'Beat', 'Offset']]
    
    for index, row in notes_df.iterrows():
        # Extract measure, beat, and offset information from the index or columns
        if isinstance(notes_df.index, pd.MultiIndex):
            # If multi-index, extract from index
            if 'Measure' in notes_df.index.names:
                measure = index[notes_df.index.names.index('Measure')] if 'Measure' in notes_df.index.names else None
            else:
                measure = None
            if 'Beat' in notes_df.index.names:
                beat = index[notes_df.index.names.index('Beat')] if 'Beat' in notes_df.index.names else None
            else:
                beat = None
            if 'Offset' in notes_df.index.names:
                offset = index[notes_df.index.names.index('Offset')] if 'Offset' in notes_df.index.names else index
            else:
                offset = index
        else:
            # If single index, offset is the index, and measure/beat might be in columns
            offset = index
            measure = row.get('Measure') if 'Measure' in notes_df.columns else None
            beat = row.get('Beat') if 'Beat' in notes_df.columns else None
        
        # Process each voice part
        for voice_name in voice_columns:
            note_value = row[voice_name]
            
            # Skip NaN values and empty cells
            if pd.isna(note_value) or note_value == '':
                continue
            
            # Parse note information
            note_type = "Rest" if str(note_value).strip() == "Rest" else "Note"
            
            # Extract pitch information if it's a note
            pitch = None
            name = None
            step = None
            octave = None
            alter = None
            
            if note_type == "Note" and str(note_value) != "Rest":
                try:
                    # Basic parsing - CRIM might give us note names like "A4", "C#5", etc.
                    note_str = str(note_value).strip()
                    name = note_str
                    
                    # Try to extract basic pitch information
                    if len(note_str) >= 2:
                        step = note_str[0].upper()
                        
                        # Look for octave (usually the last character)
                        if note_str[-1].isdigit():
                            octave = int(note_str[-1])
                        
                        # Look for accidentals
                        if '#' in note_str:
                            alter = 1
                        elif 'b' in note_str or '♭' in note_str:
                            alter = -1
                        else:
                            alter = 0
                            
                        # Calculate approximate MIDI pitch if we have step and octave
                        if step and octave is not None:
                            step_values = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
                            if step in step_values:
                                pitch = (octave + 1) * 12 + step_values[step] + (alter or 0)
                
                except Exception:
                    # If parsing fails, just store the original value
                    name = str(note_value)
            
            note_data = {
                'piece_id': piece_id,
                'voice': voice_name,  # Use voice name instead of number for now
                'onset': float(offset) if offset is not None else 0.0,
                'duration': None,  # We'll need to calculate this separately or get from durations()
                'measure': int(measure) if measure is not None and pd.notna(measure) else None,
                'beat': float(beat) if beat is not None and pd.notna(beat) else None,
                'pitch': pitch,
                'name': name,
                'step': step,
                'octave': octave,
                'alter': alter,
                'type': note_type,
                'staff': None,  # Not available in basic notes()
                'tie': None  # Not available in basic notes()
            }
            
            notes_list.append(note_data)
    
    return notes_list

def convert_notes_df_to_list(notes_df, piece_id: int) -> List[Dict]:
    """Convert notes DataFrame to list of dictionaries
    
    CRIM notes() returns a DataFrame where:
    - Each column represents a voice/part (e.g., 'Cantus', 'Altus', etc.)
    - Each row represents a time offset
    - Values are note names (e.g., 'A4', 'Rest') or NaN for no note
    """
    notes_list = []
    note_id = 1
    
    # Get metadata columns (if present)
    metadata_cols = ['Composer', 'Title', 'Date']
    voice_cols = [col for col in notes_df.columns if col not in metadata_cols]
    
    print(f"  Voice columns found: {voice_cols}")
    
    for offset, row in notes_df.iterrows():
        for voice_num, voice_name in enumerate(voice_cols, 1):
            note_value = row[voice_name]
            
            # Skip NaN values and empty cells
            if pd.isna(note_value) or note_value == '':
                continue
            
            # Parse the note value
            if note_value == 'Rest':
                note_type = 'Rest'
                pitch = None
                name = 'Rest'
                step = None
                octave = None
                alter = None
            else:
                note_type = 'Note'
                name = str(note_value)
                
                # Parse note name to extract pitch information
                # Examples: 'A4', 'C#5', 'Bb3'
                try:
                    pitch, step, octave, alter = parse_note_name(name)
                except:
                    # If parsing fails, use defaults
                    pitch = None
                    step = name[0] if name else None
                    octave = None
                    alter = None
            
            note_data = {
                'piece_id': piece_id,
                'voice': voice_num,  # Use numeric voice number
                'onset': float(offset),  # CRIM uses offset as the index
                'duration': 1.0,  # Default duration, CRIM doesn't provide this in notes()
                'measure': None,  # CRIM notes() doesn't include measure info
                'beat': None,     # CRIM notes() doesn't include beat info
                'pitch': pitch,
                'name': name,
                'step': step,
                'octave': octave,
                'alter': alter,
                'type': note_type,
                'staff': voice_num,  # Assume staff equals voice
                'tie': None  # CRIM notes() doesn't include tie info
            }
            
            notes_list.append(note_data)
            note_id += 1
    
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
