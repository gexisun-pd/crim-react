#!/usr/bin/env python3
"""
Test script to debug note_id matching for melodic intervals.
This script will help identify why notes are not being matched properly.
"""

import os
import sys
import pandas as pd

# Add the core directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from core.db.db import PiecesDB
from core.crim_cache_manager import cache_manager

def test_note_matching():
    """Test note matching logic for a specific piece"""
    
    # Initialize database
    db = PiecesDB()
    
    # Get all pieces from database
    print("📋 Retrieving pieces from database...")
    pieces = db.get_all_pieces()
    
    if not pieces:
        print("❌ No pieces found in database.")
        return
    
    # Use the first piece for testing
    test_piece = pieces[0]
    piece_id = test_piece['piece_id']
    piece_filename = test_piece['filename']
    
    print(f"🎵 Testing with piece {piece_id}: {piece_filename}")
    
    # Step 1: Get notes from database
    print("\n📊 Getting notes from database...")
    notes = get_notes_from_db(piece_id)
    
    if not notes:
        print("❌ No notes found in database for this piece.")
        return
    
    print(f"✅ Found {len(notes)} notes in database")
    
    # Print first few notes for inspection
    print("\n🔍 First 10 notes from database:")
    for i, note in enumerate(notes[:10]):
        print(f"  {i+1}. note_id={note['note_id']}, voice={note['voice']}, "
              f"onset={note['onset']}, type={note['type']}, name={note['name']}")
    
    # Step 2: Get cached DataFrames
    print(f"\n📁 Getting cached DataFrames...")
    piece_key = cache_manager._get_piece_key(piece_filename)
    
    notes_df = cache_manager.load_dataframe(piece_key, 'notes')
    detail_df = cache_manager.load_dataframe(piece_key, 'detail_index')
    melodic_intervals_df = cache_manager.load_dataframe(piece_key, 'melodic_intervals')
    
    if notes_df is None:
        print("❌ No cached notes DataFrame found")
        return
    
    print(f"✅ Found cached DataFrames:")
    print(f"   - notes_df shape: {notes_df.shape}")
    if detail_df is not None:
        print(f"   - detail_df shape: {detail_df.shape}")
    if melodic_intervals_df is not None:
        print(f"   - melodic_intervals_df shape: {melodic_intervals_df.shape}")
    
    # Step 3: Analyze DataFrame structure
    print(f"\n🔍 Analyzing DataFrame structure:")
    print(f"   - notes_df columns: {list(notes_df.columns)}")
    print(f"   - notes_df index: {notes_df.index[:5].tolist()}")
    print(f"   - notes_df index type: {type(notes_df.index)}")
    
    # Step 4: Test matching for each voice
    print(f"\n🎭 Testing note matching by voice:")
    
    # Get unique voices from database notes
    db_voices = set(note['voice'] for note in notes if note['type'] == 'Note')
    print(f"   - Voices in database: {sorted(db_voices)}")
    
    # Get voice columns from DataFrame
    metadata_cols = ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']
    df_voice_columns = [col for col in notes_df.columns if col not in metadata_cols]
    print(f"   - Voice columns in DataFrame: {df_voice_columns}")
    
    # Test matching for first voice
    if db_voices and df_voice_columns:
        test_voice = sorted(db_voices)[0]
        print(f"\n🧪 Testing matching for voice {test_voice}:")
        
        # Get notes for this voice from database
        voice_notes_db = [note for note in notes if note['voice'] == test_voice and note['type'] == 'Note']
        voice_notes_db.sort(key=lambda x: x['onset'])
        
        print(f"   - Found {len(voice_notes_db)} notes in database for voice {test_voice}")
        
        if voice_notes_db:
            print(f"   - First 5 notes from database:")
            for i, note in enumerate(voice_notes_db[:5]):
                print(f"     {i+1}. onset={note['onset']:.3f}, note_id={note['note_id']}, name={note['name']}")
        
        # Get onset values from DataFrame
        df_onsets = notes_df.index.tolist()[:10]  # First 10 onsets
        print(f"   - First 10 onsets from DataFrame: {df_onsets}")
        
        # Test specific matching
        if voice_notes_db and df_onsets:
            test_onset = df_onsets[0]
            print(f"\n🎯 Testing match for onset {test_onset}:")
            
            tolerance = 0.001
            matches = []
            for note in voice_notes_db:
                if abs(note['onset'] - test_onset) <= tolerance:
                    matches.append(note)
            
            print(f"   - Found {len(matches)} matches with tolerance {tolerance}")
            for match in matches:
                print(f"     - note_id={match['note_id']}, onset={match['onset']}, name={match['name']}")
            
            # Try different tolerances
            for tol in [0.01, 0.1, 0.5]:
                matches = []
                for note in voice_notes_db:
                    if abs(note['onset'] - test_onset) <= tol:
                        matches.append(note)
                print(f"   - With tolerance {tol}: {len(matches)} matches")
    
    # Step 5: Compare timing precision
    print(f"\n⏱️  Comparing timing precision:")
    
    if notes:
        db_onsets = [note['onset'] for note in notes[:10]]
        print(f"   - Database onsets (first 10): {db_onsets}")
        
    if notes_df is not None:
        df_onsets = notes_df.index[:10].tolist()
        print(f"   - DataFrame onsets (first 10): {df_onsets}")
        
        # Check if they're approximately equal
        if len(db_onsets) > 0 and len(df_onsets) > 0:
            print(f"   - Onset comparison:")
            for i in range(min(5, len(db_onsets), len(df_onsets))):
                diff = abs(db_onsets[i] - df_onsets[i])
                print(f"     Position {i}: DB={db_onsets[i]:.6f}, DF={df_onsets[i]:.6f}, diff={diff:.6f}")

def get_notes_from_db(piece_id: int):
    """Get all notes for a piece from database"""
    db = PiecesDB()
    
    try:
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT note_id, piece_id, voice, onset, duration, measure, beat, 
                   pitch, name, step, octave, `alter`, type, staff, tie
            FROM notes 
            WHERE piece_id = ? 
            ORDER BY voice, onset
        """, (piece_id,))
        
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        notes = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        return notes
        
    except Exception as e:
        print(f"❌ Error retrieving notes: {e}")
        return []

def test_matching_algorithm(piece_id: int, voice: int, onset: float):
    """Test the specific matching algorithm"""
    print(f"\n🔬 Testing matching algorithm:")
    print(f"   - piece_id: {piece_id}")
    print(f"   - voice: {voice}")
    print(f"   - onset: {onset}")
    
    notes = get_notes_from_db(piece_id)
    
    # Filter notes for the specific voice
    voice_notes = [note for note in notes if note['voice'] == voice and note['type'] == 'Note']
    
    if not voice_notes:
        print(f"   ❌ No notes found for voice {voice}")
        return None, None
    
    print(f"   ✅ Found {len(voice_notes)} notes for voice {voice}")
    
    # Sort by onset to ensure proper order
    voice_notes.sort(key=lambda x: x['onset'])
    
    # Find the note at the current onset
    start_note_id = None
    next_note_id = None
    
    tolerance = 0.001
    print(f"   🎯 Searching with tolerance: {tolerance}")
    
    for i, note in enumerate(voice_notes):
        diff = abs(note['onset'] - onset)
        print(f"      Note {i}: onset={note['onset']:.6f}, diff={diff:.6f}, note_id={note['note_id']}")
        
        if diff <= tolerance:
            start_note_id = note['note_id']
            print(f"      ✅ Match found! note_id={start_note_id}")
            
            # Get next note
            if i + 1 < len(voice_notes):
                next_note_id = voice_notes[i + 1]['note_id']
                print(f"      ✅ Next note: note_id={next_note_id}")
            else:
                print(f"      ⚠️  No next note available")
            break
    
    if start_note_id is None:
        print(f"   ❌ No match found with tolerance {tolerance}")
        
        # Try larger tolerance
        for tol in [0.01, 0.1, 0.5]:
            print(f"   🔍 Trying tolerance {tol}:")
            for i, note in enumerate(voice_notes):
                diff = abs(note['onset'] - onset)
                if diff <= tol:
                    print(f"      ✅ Would match with tolerance {tol}: note_id={note['note_id']}, diff={diff:.6f}")
                    break
            else:
                print(f"      ❌ Still no match with tolerance {tol}")
    
    return start_note_id, next_note_id

if __name__ == "__main__":
    print("🧪 Testing Note ID Matching for Melodic Intervals")
    print("=" * 60)
    
    test_note_matching()
    
    # Additional specific test - use the first piece from database
    print(f"\n" + "=" * 60)
    print("🎯 Testing specific case:")
    
    # Get the first piece from database for testing
    db = PiecesDB()
    pieces = db.get_all_pieces()
    if pieces:
        test_piece = pieces[0]
        test_piece_id = test_piece['piece_id']
        test_voice = 1  # Use voice 1
        test_onset = 0.0  # Use onset 0.0
        print(f"Using piece {test_piece_id}: {test_piece['filename']}")
        test_matching_algorithm(piece_id=test_piece_id, voice=test_voice, onset=test_onset)
    else:
        print("No pieces found in database")
