import os
import sys
from typing import List, Dict, Optional
import pandas as pd

# Add the core directory to the path to import db module
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db.db import PiecesDB

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
    """Extract notes from a piece using CRIM intervals library"""
    if not CRIM_INTERVALS_AVAILABLE:
        raise ImportError("crim_intervals library is required for note extraction")
    
    try:
        print(f"  Creating corpus and extracting notes...")
        
        # Create a corpus with just this piece
        corpus = CorpusBase([file_path])
        
        # Use the batch method to extract notes according to CRIM documentation
        # We'll try different ways to access the notes function
        try:
            if ImportedPiece:
                func = ImportedPiece.notes
            else:
                # Try to get it from the crim_intervals module
                func = getattr(crim_intervals, 'ImportedPiece').notes
        except AttributeError:
            # Fallback: try accessing through the scores directly
            if hasattr(corpus, 'scores') and len(corpus.scores) > 0:
                piece = corpus.scores[0]
                notes_df = piece.notes()
                
                if notes_df.empty:
                    print(f"  Warning: No notes found in {file_path}")
                    return []
                
                print(f"  Found {len(notes_df)} notes")
                return convert_notes_df_to_list(notes_df, piece_id)
            else:
                raise AttributeError("Cannot access notes function")
        
        # Use batch method
        list_of_dfs = corpus.batch(func, metadata=True)
        
        if not list_of_dfs or len(list_of_dfs) == 0:
            print(f"  Warning: No notes found in {file_path}")
            return []
        
        # Get the notes DataFrame (should be the first and only one in our list)
        notes_df = list_of_dfs[0]
        
        if notes_df.empty:
            print(f"  Warning: Empty notes DataFrame for {file_path}")
            return []
        
        print(f"  Found {len(notes_df)} notes")
        
        return convert_notes_df_to_list(notes_df, piece_id)
        
    except Exception as e:
        print(f"  Error extracting notes from {file_path}: {e}")
        raise

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
