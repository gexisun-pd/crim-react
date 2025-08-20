import os
import sys
import sqlite3
import traceback
from typing import List, Dict, Optional, Set
import pandas as pd

# Add the core directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db.db import PiecesDB
from crim_cache_manager import cache_manager

# Import crim_intervals for note entry extraction
try:
    import crim_intervals
    from crim_intervals import CorpusBase
    CRIM_INTERVALS_AVAILABLE = True
except ImportError:
    print("Error: crim_intervals library is required but not available.")
    print("Please install crim_intervals")
    CRIM_INTERVALS_AVAILABLE = False

def extract_note_entries_from_piece(file_path: str, piece_id: int, note_set_id: int, 
                                   combine_unisons: bool, note_set_slug: str) -> Optional[Set[int]]:
    """
    Extract note entries from a piece using n=1 entries and notes dataframe
    
    This function identifies which notes are entry points by using CRIM's entries() function
    with n=1 applied directly to the notes dataframe.
    
    Returns:
        Set of note_ids that are entry points, or None if error
    """
    if not CRIM_INTERVALS_AVAILABLE:
        raise ImportError("crim_intervals library is required for note entry extraction")
    
    filename = os.path.basename(file_path)
    piece_key = cache_manager._get_piece_key(filename)
    
    # Try to load cached note entries first using custom approach
    try:
        import pickle
        cache_dir = cache_manager.cache_dir
        stage_dir = os.path.join(cache_dir, 'pkl', 'note_entries', note_set_slug)
        piece_dir = os.path.join(stage_dir, piece_key)
        entry_ids_file = os.path.join(piece_dir, 'entry_note_ids.pkl')
        
        if os.path.exists(entry_ids_file):
            print(f"    Using cache")
            
            # Load entry note_ids from pickle file
            with open(entry_ids_file, 'rb') as f:
                entry_note_ids_list = pickle.load(f)
            
            # Convert list back to set
            entry_note_ids = set(entry_note_ids_list)
            return entry_note_ids
    except Exception as cache_error:
        pass  # Silently proceed with fresh extraction
    
    try:
        print(f"    Extracting...")
        
        # Create a corpus with just this piece
        corpus = CorpusBase([file_path])
        
        # Access the piece from corpus.scores
        if not hasattr(corpus, 'scores') or len(corpus.scores) == 0:
            print(f"    Error: No scores found")
            return set()
        
        piece = corpus.scores[0]
        
        try:
            # Step 1: Extract notes with specified combineUnisons parameter
            notes_df = piece.notes(combineUnisons=combine_unisons)
            
            # Step 2: Apply entries() function directly to notes dataframe with n=1
            entries_df = piece.entries(
                df=notes_df,         # Use notes dataframe directly
                n=1,                 # n=1 for individual note entries
                thematic=False,      # Don't require thematic (multiple occurrences)
                anywhere=True,       # Include all instances, not just from rests
                fermatas=True        # Include entries after fermatas
            )
            
        except Exception as e:
            print(f"    Error in CRIM extraction: {e}")
            return set()
        
        if entries_df is None or entries_df.empty:
            print(f"    Warning: No entries found")
            return set()
        
        # Convert entries DataFrame to set of note_ids
        entry_note_ids = convert_note_entries_to_note_ids(entries_df, piece_id, note_set_id)
        
        # Save note entries to cache with custom approach for mixed data types
        try:
            import pickle
            cache_dir = cache_manager.cache_dir
            stage_dir = os.path.join(cache_dir, 'pkl', 'note_entries', note_set_slug)
            piece_dir = os.path.join(stage_dir, piece_key)
            os.makedirs(piece_dir, exist_ok=True)
            
            # Save entries DataFrame as pickle
            entries_df.to_pickle(os.path.join(piece_dir, 'entries.pkl'))
            
            # Save entry_note_ids as simple pickle file
            with open(os.path.join(piece_dir, 'entry_note_ids.pkl'), 'wb') as f:
                pickle.dump(list(entry_note_ids), f)
            
            # Save metadata as JSON
            import json
            metadata = {
                'file_path': file_path,
                'piece_id': piece_id,
                'note_set_id': note_set_id,
                'combine_unisons': combine_unisons,
                'note_set_slug': note_set_slug,
                'extraction_method': 'crim_intervals_note_entries',
                'n': 1,
                'end_parameter': False,
                'thematic': False,
                'anywhere': True,
                'fermatas': True,
                'offsets': 'first'
            }
            with open(os.path.join(piece_dir, 'metadata.json'), 'w') as f:
                json.dump(metadata, f, indent=2)
            
        except Exception as cache_error:
            pass  # Silently continue without caching
        
        return entry_note_ids
        
    except Exception as e:
        print(f"    Error: {e}")
        raise

def convert_note_entries_to_note_ids(entries_df: pd.DataFrame, piece_id: int, note_set_id: int) -> Set[int]:
    """
    Convert note entries DataFrame to set of note_ids that are entry points
    
    This function processes CRIM's entries output (n=1 applied to notes) and matches
    the entry points with corresponding note_ids from the database.
    """
    if entries_df is None or entries_df.empty:
        return set()
    
    # Get database connection to lookup note_ids
    db = PiecesDB()
    
    # Get voice columns (exclude metadata columns)
    metadata_cols = ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']
    voice_columns = [col for col in entries_df.columns if col not in metadata_cols]
    
    entry_note_ids = set()
    
    # Iterate through each row (time point) of the DataFrame
    for idx, row in entries_df.iterrows():
        # Extract timing information (onset)
        offset = idx
        
        # Check if we have multi-index or columns with timing info
        if isinstance(entries_df.index, pd.MultiIndex):
            # Multi-index case (Offset, Measure, Beat)
            if len(idx) >= 1:
                offset = idx[0]
        else:
            # Single index
            if 'Offset' in entries_df.columns:
                offset = row.get('Offset')
        
        # Process each voice at this time point
        for voice_idx, voice_name in enumerate(voice_columns, 1):
            entry_value = entries_df.loc[idx, voice_name]
            
            # Skip if no entry value or if it's NaN/None/empty
            if pd.isna(entry_value) or entry_value == '' or entry_value is None:
                continue
            
            # This onset/voice combination has an entry, so we need to find the corresponding note_id
            try:
                notes_at_position = db.get_note_ids_for_piece_and_voice(piece_id, voice_idx, note_set_id)
                
                # Find the note with matching onset
                for note in notes_at_position:
                    if abs(note['onset'] - float(offset)) < 1e-6:  # Small tolerance for float comparison
                        entry_note_ids.add(note['note_id'])
                        break
                        
            except Exception as e:
                continue
    
    return entry_note_ids

def ingest_note_entries_for_all_pieces():
    """Main function to identify note entries for all pieces using all note sets"""
    
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
    
    # Get all note sets
    note_sets = db.get_all_note_sets()
    
    if not note_sets:
        print("No note sets found in database.")
        print("Please run core/db/init_db.py first to create note sets.")
        return
    
    print(f"Found {len(note_sets)} note sets")
    
    # Get project root directory (two levels up from core/ingest/)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_root = os.path.join(project_root, 'data')
    
    total_combinations = len(pieces) * len(note_sets)
    processed_count = 0
    skipped_count = 0
    error_count = 0
    total_entries_found = 0
    total_notes_updated = 0
    
    print(f"\n=== Processing {total_combinations} combinations ===")
    
    # Process each note set
    for note_set in note_sets:
        note_set_id = note_set['set_id']
        note_set_slug = note_set['slug']
        combine_unisons = bool(note_set['combine_unisons'])
        
        print(f"\n--- Note Set {note_set_id}: {note_set_slug} (combine_unisons={combine_unisons}) ---")
        
        set_processed = 0
        set_skipped = 0
        set_errors = 0
        set_entries_found = 0
        set_notes_updated = 0
        
        # Process each piece with this note set
        for i, piece in enumerate(pieces, 1):
            piece_id = piece['piece_id']
            piece_path = piece['path']
            piece_filename = piece['filename']
            
            print(f"  {i}/{len(pieces)}: {piece_filename}")
            
            try:
                # Construct full file path
                full_file_path = os.path.join(data_root, piece_path)
                
                if not os.path.exists(full_file_path):
                    print(f"    Error: File not found")
                    error_count += 1
                    set_errors += 1
                    continue
                
                # Extract note entries from the piece
                entry_note_ids = extract_note_entries_from_piece(
                    full_file_path, piece_id, note_set_id, combine_unisons, note_set_slug
                )
                
                if entry_note_ids is None:
                    print(f"    Error: Could not extract entries")
                    error_count += 1
                    set_errors += 1
                    continue
                
                # Get all notes for this piece and note set to update is_entry field
                all_notes = db.get_note_ids_for_piece_and_voice_all(piece_id, note_set_id)
                
                if not all_notes:
                    print(f"    Warning: No notes found")
                    processed_count += 1
                    set_processed += 1
                    continue
                
                # Prepare batch update data
                notes_to_update = []
                for note in all_notes:
                    note_id = note['note_id']
                    is_entry = note_id in entry_note_ids
                    notes_to_update.append({
                        'note_id': note_id,
                        'is_entry': is_entry
                    })
                
                # Update is_entry field for all notes of this piece/set combination
                updated_count = db.update_notes_is_entry_batch(notes_to_update)
                
                if updated_count == len(notes_to_update):
                    print(f"    ✓ Updated {updated_count} notes, found {len(entry_note_ids)} entries")
                    processed_count += 1
                    set_processed += 1
                    set_entries_found += len(entry_note_ids)
                    total_entries_found += len(entry_note_ids)
                    set_notes_updated += updated_count
                    total_notes_updated += updated_count
                else:
                    print(f"    Warning: Only {updated_count}/{len(notes_to_update)} notes updated")
                    error_count += 1
                    set_errors += 1
                    
            except Exception as e:
                print(f"    Error: {e}")
                error_count += 1
                set_errors += 1
                continue
        
        # Print set summary
        print(f"  → Processed: {set_processed}, Errors: {set_errors}, Entries: {set_entries_found}, Notes: {set_notes_updated}")
    
    # Print overall summary
    print(f"\n=== Summary ===")
    print(f"Note sets: {len(note_sets)}, Pieces: {len(pieces)}")
    print(f"Processed: {processed_count}, Errors: {error_count}")
    print(f"Total entry points found: {total_entries_found}")
    print(f"Total notes updated: {total_notes_updated}")

if __name__ == "__main__":
    ingest_note_entries_for_all_pieces()
