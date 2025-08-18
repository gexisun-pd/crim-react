#!/usr/bin/env python3
"""
测试脚本：诊断notes缺失问题
比较crim_intervals和music21提取的差异
"""

import os
import sys
import sqlite3
import pandas as pd

# Add necessary paths
sys.path.append('core')
from db.db import PiecesDB

# Import both libraries for comparison
try:
    import crim_intervals
    from crim_intervals import CorpusBase
    CRIM_INTERVALS_AVAILABLE = True
    print("✓ crim_intervals available")
except ImportError:
    CRIM_INTERVALS_AVAILABLE = False
    print("✗ crim_intervals not available")

try:
    from music21 import converter, stream, note, chord, meter, tempo
    MUSIC21_AVAILABLE = True
    print("✓ music21 available")
except ImportError:
    MUSIC21_AVAILABLE = False
    print("✗ music21 not available")

def extract_notes_with_crim(file_path, combine_unisons=True):
    """使用crim_intervals提取notes"""
    if not CRIM_INTERVALS_AVAILABLE:
        return None, None, None
    
    print(f"\n--- Using CRIM Intervals ---")
    print(f"File: {os.path.basename(file_path)}")
    print(f"combineUnisons: {combine_unisons}")
    
    try:
        corpus = CorpusBase([file_path])
        piece = corpus.scores[0]
        
        # Get notes and details
        notes_df = piece.notes(combineUnisons=combine_unisons)
        durations_df = piece.durations()
        detail_df = piece.detailIndex(notes_df, measure=True, beat=True, offset=True)
        
        print(f"Notes DataFrame shape: {notes_df.shape}")
        print(f"Detail DataFrame shape: {detail_df.shape}")
        print(f"Durations DataFrame shape: {durations_df.shape}")
        
        # Show column info
        print(f"Notes columns: {list(notes_df.columns)}")
        print(f"Index: {notes_df.index.names if hasattr(notes_df.index, 'names') else 'Simple index'}")
        
        # Show first few rows
        print("\nFirst 10 rows of notes:")
        print(notes_df.head(10))
        
        # Show measure distribution
        if 'Measure' in detail_df.columns:
            measure_counts = detail_df.groupby('Measure').size()
            print(f"\nNotes by measure (CRIM):")
            for measure, count in measure_counts.head(10).items():
                print(f"  Measure {measure}: {count} notes")
        
        return notes_df, durations_df, detail_df
        
    except Exception as e:
        print(f"Error with CRIM: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def extract_notes_with_music21(file_path):
    """使用music21提取notes"""
    if not MUSIC21_AVAILABLE:
        return None
    
    print(f"\n--- Using Music21 ---")
    print(f"File: {os.path.basename(file_path)}")
    
    try:
        score = converter.parse(file_path)
        
        # Get all notes and rests
        notes_data = []
        
        for part_idx, part in enumerate(score.parts):
            part_name = part.partName or f"Part_{part_idx + 1}"
            print(f"Processing part: {part_name}")
            
            # Get all notes and rests in this part
            elements = part.flatten().notesAndRests
            
            for element in elements:
                measure_num = None
                beat = None
                
                # Try to get measure number
                try:
                    measure_num = element.measureNumber
                except:
                    pass
                
                # Try to get beat
                try:
                    beat = element.beat
                except:
                    pass
                
                note_data = {
                    'part': part_idx + 1,
                    'part_name': part_name,
                    'offset': float(element.offset),
                    'duration': float(element.duration.quarterLength),
                    'measure': measure_num,
                    'beat': beat,
                    'type': 'Note' if isinstance(element, note.Note) else 
                            'Chord' if isinstance(element, note.Chord) else 'Rest',
                    'pitch': element.pitch.midi if hasattr(element, 'pitch') and element.pitch else None,
                    'name': str(element.pitch) if hasattr(element, 'pitch') and element.pitch else 'Rest'
                }
                notes_data.append(note_data)
        
        music21_df = pd.DataFrame(notes_data)
        print(f"Music21 DataFrame shape: {music21_df.shape}")
        
        if not music21_df.empty:
            print(f"Columns: {list(music21_df.columns)}")
            
            # Show first few rows
            print("\nFirst 10 rows of music21 notes:")
            print(music21_df.head(10))
            
            # Show measure distribution
            if 'measure' in music21_df.columns:
                measure_counts = music21_df.groupby('measure').size()
                print(f"\nNotes by measure (Music21):")
                for measure, count in measure_counts.head(10).items():
                    print(f"  Measure {measure}: {count} notes")
        
        return music21_df
        
    except Exception as e:
        print(f"Error with Music21: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_extractions(crim_detail_df, music21_df):
    """比较两种提取方法的结果"""
    print(f"\n--- Comparison ---")
    
    if crim_detail_df is not None and not crim_detail_df.empty:
        crim_total = len(crim_detail_df)
        crim_voices = len([col for col in crim_detail_df.columns if col not in ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']])
        print(f"CRIM: {crim_total} time points, {crim_voices} voices")
        
        # Calculate actual note count (excluding NaN)
        crim_note_count = 0
        voice_cols = [col for col in crim_detail_df.columns if col not in ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']]
        for col in voice_cols:
            crim_note_count += crim_detail_df[col].notna().sum()
        print(f"CRIM: {crim_note_count} actual notes (non-NaN)")
    else:
        print("CRIM: No data")
    
    if music21_df is not None and not music21_df.empty:
        music21_total = len(music21_df)
        music21_parts = music21_df['part'].nunique()
        print(f"Music21: {music21_total} notes/rests, {music21_parts} parts")
        
        # Count actual notes (not rests)
        music21_note_count = len(music21_df[music21_df['type'] != 'Rest'])
        print(f"Music21: {music21_note_count} actual notes (excluding rests)")
    else:
        print("Music21: No data")
    
    # Check for specific measure 2 data
    print(f"\n--- Measure 2 Analysis ---")
    
    if crim_detail_df is not None and not crim_detail_df.empty:
        if 'Measure' in crim_detail_df.columns:
            measure_2_crim = crim_detail_df[crim_detail_df['Measure'] == 2]
            if not measure_2_crim.empty:
                voice_cols = [col for col in measure_2_crim.columns if col not in ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']]
                m2_note_count = 0
                for col in voice_cols:
                    m2_note_count += measure_2_crim[col].notna().sum()
                print(f"CRIM Measure 2: {len(measure_2_crim)} time points, {m2_note_count} notes")
                print("CRIM Measure 2 data:")
                print(measure_2_crim[voice_cols].head())
            else:
                print("CRIM Measure 2: No data found")
        else:
            print("CRIM: No measure information available")
    
    if music21_df is not None and not music21_df.empty:
        if 'measure' in music21_df.columns:
            measure_2_music21 = music21_df[music21_df['measure'] == 2]
            if not measure_2_music21.empty:
                print(f"Music21 Measure 2: {len(measure_2_music21)} elements")
                print("Music21 Measure 2 data:")
                print(measure_2_music21[['part_name', 'offset', 'duration', 'measure', 'beat', 'type', 'name']].head())
            else:
                print("Music21 Measure 2: No data found")
        else:
            print("Music21: No measure information available")

def check_database_notes(piece_id=1):
    """检查数据库中的notes数据"""
    print(f"\n--- Database Analysis for Piece {piece_id} ---")
    
    try:
        db = PiecesDB()
        project_root = os.path.dirname(__file__)
        db_path = os.path.join(project_root, 'database', 'analysis.db')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check total notes
        cursor.execute("SELECT COUNT(*) FROM notes WHERE piece_id = ?", (piece_id,))
        total_notes = cursor.fetchone()[0]
        print(f"Total notes in database for piece {piece_id}: {total_notes}")
        
        # Check by measure
        cursor.execute("""
            SELECT measure, COUNT(*) as count 
            FROM notes 
            WHERE piece_id = ? AND measure IS NOT NULL 
            GROUP BY measure 
            ORDER BY measure
        """, (piece_id,))
        
        measure_data = cursor.fetchall()
        print("Notes by measure in database:")
        for measure, count in measure_data:
            print(f"  Measure {measure}: {count} notes")
        
        # Check measure 2 specifically
        cursor.execute("""
            SELECT voice, voice_name, onset, duration, measure, beat, pitch, name, type
            FROM notes 
            WHERE piece_id = ? AND measure = 2 
            ORDER BY voice, onset
        """, (piece_id,))
        
        measure_2_notes = cursor.fetchall()
        if measure_2_notes:
            print(f"\nMeasure 2 detailed notes ({len(measure_2_notes)} total):")
            for note in measure_2_notes[:10]:  # Show first 10
                voice, voice_name, onset, duration, measure, beat, pitch, name, note_type = note
                print(f"  Voice {voice} ({voice_name}): onset={onset}, dur={duration}, beat={beat}, pitch={pitch}, name={name}")
        else:
            print("No notes found in measure 2 in database")
        
        # Check for NULL measure notes
        cursor.execute("SELECT COUNT(*) FROM notes WHERE piece_id = ? AND measure IS NULL", (piece_id,))
        null_measures = cursor.fetchone()[0]
        print(f"Notes with NULL measure: {null_measures}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking database: {e}")

def test_specific_file(file_path, piece_id=1):
    """测试特定文件的notes提取"""
    print(f"\n{'='*60}")
    print(f"Testing file: {os.path.basename(file_path)}")
    print(f"{'='*60}")
    
    # Test with CRIM intervals
    crim_notes, crim_durations, crim_detail = extract_notes_with_crim(file_path, combine_unisons=True)
    
    # Test with Music21
    music21_notes = extract_notes_with_music21(file_path)
    
    # Compare results
    compare_extractions(crim_detail, music21_notes)
    
    # Check database
    check_database_notes(piece_id)

def main():
    """主测试函数"""
    print("Notes Extraction Diagnosis Test")
    print("="*50)
    
    # Test with a specific file
    test_file = "data/test/Gabrieli_C001_Inclina_Domine_6vv.musicxml"
    
    if os.path.exists(test_file):
        test_specific_file(test_file, piece_id=1)
    else:
        print(f"Test file not found: {test_file}")
        
        # Try to find any test file
        test_dir = "data/test"
        if os.path.exists(test_dir):
            files = [f for f in os.listdir(test_dir) if f.endswith(('.xml', '.musicxml'))]
            if files:
                test_file = os.path.join(test_dir, files[0])
                print(f"Using: {test_file}")
                test_specific_file(test_file, piece_id=1)
            else:
                print("No test files found in data/test")
        else:
            print("Test directory not found")

if __name__ == "__main__":
    main()
