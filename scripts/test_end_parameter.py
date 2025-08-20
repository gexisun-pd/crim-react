#!/usr/bin/env python3
"""
Test script to compare the effects of end=True vs end=False in melodic intervals extraction.
This script will show the differences in how intervals are positioned and matched.
"""

import os
import sys
import pandas as pd

# Add the core directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from core.db.db import PiecesDB
from core.crim_cache_manager import cache_manager

try:
    import crim_intervals
    from crim_intervals import CorpusBase
    CRIM_INTERVALS_AVAILABLE = True
except ImportError:
    print("❌ crim_intervals library not available")
    CRIM_INTERVALS_AVAILABLE = False

def test_end_parameter_effects():
    """Test the differences between end=True and end=False"""
    
    if not CRIM_INTERVALS_AVAILABLE:
        print("❌ Cannot test without crim_intervals library")
        return
    
    # Get a test piece from database
    db = PiecesDB()
    pieces = db.get_all_pieces()
    
    if not pieces:
        print("❌ No pieces found in database")
        return
    
    test_piece = pieces[0]
    piece_id = test_piece['piece_id']
    piece_filename = test_piece['filename']
    
    print(f"🎵 Testing with piece {piece_id}: {piece_filename}")
    
    # Get the piece file path
    project_root = os.path.dirname(os.path.dirname(__file__))
    data_root = os.path.join(project_root, 'data')
    full_file_path = os.path.join(data_root, test_piece['path'])
    
    if not os.path.exists(full_file_path):
        print(f"❌ File not found: {full_file_path}")
        return
    
    try:
        print(f"\n📊 Creating corpus and extracting data...")
        
        # Create corpus
        corpus = CorpusBase([full_file_path])
        piece = corpus.scores[0]
        
        # Get basic notes first for reference
        notes_df = piece.notes()
        print(f"   - Notes DataFrame shape: {notes_df.shape}")
        print(f"   - Voice columns: {list(notes_df.columns)}")
        
        # Show first few notes for context
        print(f"\n📝 First few notes for reference:")
        print(notes_df.head(10))
        
        print(f"\n" + "="*80)
        print(f"🧪 TESTING end=True (default behavior)")
        print(f"="*80)
        
        # Extract melodic intervals with end=True (default)
        melodic_end_true = piece.melodic(end=True)
        print(f"   - Melodic intervals (end=True) shape: {melodic_end_true.shape}")
        print(f"   - Columns: {list(melodic_end_true.columns)}")
        
        if not melodic_end_true.empty:
            print(f"\n📋 First 10 melodic intervals (end=True):")
            print(f"   Index (onset positions): {melodic_end_true.index[:10].tolist()}")
            
            # Show detailed view
            detail_true = piece.detailIndex(melodic_end_true, measure=True, beat=True, offset=True)
            print(f"\n📊 Detailed view (end=True) - first 10 rows:")
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            print(detail_true.head(10))
        
        print(f"\n" + "="*80)
        print(f"🧪 TESTING end=False")
        print(f"="*80)
        
        # Extract melodic intervals with end=False
        melodic_end_false = piece.melodic(end=False)
        print(f"   - Melodic intervals (end=False) shape: {melodic_end_false.shape}")
        print(f"   - Columns: {list(melodic_end_false.columns)}")
        
        if not melodic_end_false.empty:
            print(f"\n📋 First 10 melodic intervals (end=False):")
            print(f"   Index (onset positions): {melodic_end_false.index[:10].tolist()}")
            
            # Show detailed view
            detail_false = piece.detailIndex(melodic_end_false, measure=True, beat=True, offset=True)
            print(f"\n📊 Detailed view (end=False) - first 10 rows:")
            print(detail_false.head(10))
        
        print(f"\n" + "="*80)
        print(f"🔍 COMPARISON ANALYSIS")
        print(f"="*80)
        
        if not melodic_end_true.empty and not melodic_end_false.empty:
            # Compare onset positions
            onsets_true = melodic_end_true.index[:20].tolist()
            onsets_false = melodic_end_false.index[:20].tolist()
            
            print(f"\n⏰ Onset Position Comparison (first 20 intervals):")
            print(f"   end=True  onsets: {onsets_true}")
            print(f"   end=False onsets: {onsets_false}")
            
            # Calculate differences
            min_len = min(len(onsets_true), len(onsets_false))
            differences = []
            for i in range(min_len):
                diff = onsets_true[i] - onsets_false[i]
                differences.append(diff)
            
            print(f"\n📊 Onset Differences (end=True - end=False):")
            print(f"   First 10 differences: {differences[:10]}")
            
            if differences:
                avg_diff = sum(differences) / len(differences)
                print(f"   Average difference: {avg_diff:.6f}")
                print(f"   Range: {min(differences):.6f} to {max(differences):.6f}")
        
        # Test note matching for both approaches
        print(f"\n" + "="*80)
        print(f"🎯 NOTE MATCHING TEST")
        print(f"="*80)
        
        # Get notes from database for comparison
        notes_from_db = get_notes_from_db(piece_id)
        if notes_from_db:
            voice_1_notes = [n for n in notes_from_db if n['voice'] == 1 and n['type'] == 'Note']
            voice_1_notes.sort(key=lambda x: x['onset'])
            
            print(f"\n🎵 Voice 1 notes from database (first 10):")
            for i, note in enumerate(voice_1_notes[:10]):
                print(f"   {i+1:2d}. onset={note['onset']:6.3f}, note_id={note['note_id']:3d}, name={note['name']}")
            
            # Test matching for end=True
            print(f"\n🧪 Testing note matching for end=True intervals:")
            test_note_matching_for_intervals(piece_id, melodic_end_true, voice_1_notes, "end=True")
            
            # Test matching for end=False
            print(f"\n🧪 Testing note matching for end=False intervals:")
            test_note_matching_for_intervals(piece_id, melodic_end_false, voice_1_notes, "end=False")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

def test_note_matching_for_intervals(piece_id: int, intervals_df, voice_notes: list, label: str):
    """Test note matching for a specific intervals DataFrame"""
    
    if intervals_df.empty:
        print(f"   ❌ No intervals to test for {label}")
        return
    
    # Get first voice column
    voice_columns = [col for col in intervals_df.columns if col not in ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']]
    if not voice_columns:
        print(f"   ❌ No voice columns found for {label}")
        return
    
    first_voice_col = voice_columns[0]
    
    # Test first 5 intervals
    matches_found = 0
    total_tested = 0
    
    print(f"   🔍 Testing first 5 intervals from {first_voice_col}:")
    
    for i, (onset, row) in enumerate(intervals_df.head(5).iterrows()):
        interval_value = row[first_voice_col]
        
        if pd.isna(interval_value) or interval_value == '':
            continue
        
        total_tested += 1
        
        # Try to find matching note
        tolerance = 0.001
        matched_notes = []
        
        for note in voice_notes:
            if abs(note['onset'] - onset) <= tolerance:
                matched_notes.append(note)
        
        if matched_notes:
            matches_found += 1
            note = matched_notes[0]
            print(f"     ✅ Onset {onset:6.3f}: interval={interval_value:>8s} → matched note_id={note['note_id']:3d} ({note['name']})")
        else:
            # Find closest note
            closest_note = min(voice_notes, key=lambda n: abs(n['onset'] - onset))
            diff = abs(closest_note['onset'] - onset)
            print(f"     ❌ Onset {onset:6.3f}: interval={interval_value:>8s} → no match (closest: {closest_note['onset']:6.3f}, diff={diff:.3f})")
    
    match_rate = (matches_found / total_tested * 100) if total_tested > 0 else 0
    print(f"   📊 {label} matching rate: {matches_found}/{total_tested} ({match_rate:.1f}%)")

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

def analyze_interval_patterns():
    """Analyze the pattern differences between end=True and end=False"""
    
    print(f"\n" + "="*80)
    print(f"📈 THEORETICAL ANALYSIS")
    print(f"="*80)
    
    print(f"""
🎵 Understanding end=True vs end=False:

🔸 end=True (default):
   - Associates intervals with the SECOND note of the pair
   - If C5 at offset 1.0 → D5 at offset 2.0
   - The M2 interval appears at offset 2.0
   - This is the standard CRIM behavior

🔸 end=False:
   - Associates intervals with the FIRST note of the pair  
   - If C5 at offset 1.0 → D5 at offset 2.0
   - The M2 interval appears at offset 1.0
   - Interval timing shifted earlier

🎯 Implications for note matching:
   - end=True: interval onset matches the target note
   - end=False: interval onset matches the source note
   - Database note_id matching strategy should align with chosen method
   
🔄 Current implementation uses end=False, so:
   - Intervals are positioned at the first note
   - note_id should reference the starting note of the interval
   - next_note_id should reference the ending note of the interval
""")

if __name__ == "__main__":
    print("🧪 Testing end=True vs end=False Effects in Melodic Intervals")
    print("=" * 80)
    
    test_end_parameter_effects()
    analyze_interval_patterns()
    
    print(f"\n" + "=" * 80)
    print("✅ Test completed!")
