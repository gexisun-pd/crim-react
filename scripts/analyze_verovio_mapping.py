#!/usr/bin/env python3
"""
Script to analyze Verovio SVG output and understand note positioning
"""

import os
import sys
import json
from xml.etree import ElementTree as ET

# Add the core directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
from db.db import PiecesDB

def analyze_musicxml_structure(piece_id=1):
    """
    Analyze the MusicXML structure to understand how notes are organized
    """
    print(f"=== Analyzing MusicXML Structure for Piece {piece_id} ===")
    
    try:
        db = PiecesDB()
        piece = db.get_piece_by_id(piece_id)
        
        if not piece:
            print(f"Piece {piece_id} not found in database")
            return
        
        # Get file path
        file_path = piece.get('path')
        if not os.path.isabs(file_path):
            base_path = os.path.join(os.path.dirname(__file__), '..', 'data')
            file_path = os.path.join(base_path, file_path)
        
        file_path = os.path.normpath(file_path)
        
        if not os.path.exists(file_path):
            print(f"MusicXML file not found: {file_path}")
            return
        
        print(f"File: {piece['filename']}")
        print(f"Path: {file_path}")
        
        # Parse MusicXML
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        print(f"Root element: {root.tag}")
        
        # Find all parts
        parts = root.findall('.//part')
        print(f"Number of parts: {len(parts)}")
        
        note_count = 0
        measure_count = 0
        
        for part_idx, part in enumerate(parts[:2]):  # Analyze first 2 parts
            part_id = part.get('id', f'part_{part_idx}')
            print(f"\n--- Part {part_idx + 1} (ID: {part_id}) ---")
            
            measures = part.findall('.//measure')
            print(f"Measures in this part: {len(measures)}")
            
            for measure_idx, measure in enumerate(measures[:3]):  # First 3 measures
                measure_number = measure.get('number', measure_idx + 1)
                print(f"\n  Measure {measure_number}:")
                
                # Find notes in this measure
                notes = measure.findall('.//note')
                print(f"    Notes: {len(notes)}")
                
                for note_idx, note in enumerate(notes[:5]):  # First 5 notes per measure
                    # Extract note information
                    pitch_elem = note.find('pitch')
                    staff_elem = note.find('staff')
                    voice_elem = note.find('voice')
                    duration_elem = note.find('duration')
                    
                    pitch_info = "Rest"
                    if pitch_elem is not None:
                        step = pitch_elem.find('step')
                        octave = pitch_elem.find('octave')
                        if step is not None and octave is not None:
                            pitch_info = f"{step.text}{octave.text}"
                    
                    staff_info = staff_elem.text if staff_elem is not None else "1"
                    voice_info = voice_elem.text if voice_elem is not None else "1"
                    duration_info = duration_elem.text if duration_elem is not None else "N/A"
                    
                    print(f"      Note {note_idx + 1}: {pitch_info}, Staff={staff_info}, Voice={voice_info}, Duration={duration_info}")
                    
                    note_count += 1
                
                measure_count += 1
        
        print(f"\n=== Summary ===")
        print(f"Total parts analyzed: {min(len(parts), 2)}")
        print(f"Total measures analyzed: {measure_count}")
        print(f"Total notes found: {note_count}")
        
        # Get database notes for comparison
        notes_db = db.get_notes_for_piece(piece_id)
        print(f"Notes in database: {len(notes_db)}")
        
        if len(notes_db) > 0:
            print("\nFirst 5 database notes:")
            for i, note in enumerate(notes_db[:5]):
                print(f"  Note {i+1}: onset={note['onset']}, voice={note['voice']}, pitch={note.get('name', 'N/A')}")
        
    except Exception as e:
        print(f"Error analyzing MusicXML: {e}")
        import traceback
        traceback.print_exc()

def create_test_mapping_data(piece_id=1):
    """
    Create a mapping between MusicXML positions and database notes
    This simulates what we would need to do in the frontend
    """
    print(f"\n=== Creating Test Mapping Data for Piece {piece_id} ===")
    
    try:
        db = PiecesDB()
        notes_db = db.get_notes_for_piece(piece_id)
        
        print(f"Database notes count: {len(notes_db)}")
        
        # Create a simplified mapping based on note order
        # In reality, we would need to match based on measure, staff, voice, and timing
        mapping_data = []
        
        for i, note in enumerate(notes_db[:10]):  # First 10 notes for testing
            mapping_data.append({
                'svg_index': i,  # This would be the order in SVG
                'note_id': note['note_id'],
                'piece_id': piece_id,
                'voice': note['voice'],
                'onset': note['onset'],
                'pitch': note.get('name', 'Unknown'),
                'measure': note.get('measure', 1),
                'search_params': {
                    'piece_id': piece_id,
                    'voice': note['voice'],
                    'onset': note['onset']
                }
            })
        
        print("Sample mapping data:")
        for item in mapping_data[:3]:
            print(f"  SVG Index {item['svg_index']}: note_id={item['note_id']}, voice={item['voice']}, onset={item['onset']}")
        
        # Save mapping to a test file
        output_file = os.path.join(os.path.dirname(__file__), 'test_note_mapping.json')
        with open(output_file, 'w') as f:
            json.dump(mapping_data, f, indent=2)
        
        print(f"\nMapping data saved to: {output_file}")
        
        return mapping_data
        
    except Exception as e:
        print(f"Error creating mapping data: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_note_id_lookup():
    """
    Test the note_id lookup functionality using existing tools
    """
    print(f"\n=== Testing Note ID Lookup ===")
    
    try:
        # Import the existing NoteIdUpdater
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core', 'utils'))
        from note_id_updater import NoteIdUpdater
        
        updater = NoteIdUpdater()
        
        # Get some sample notes from database to test with
        db = PiecesDB()
        notes_db = db.get_notes_for_piece(1)
        
        if len(notes_db) == 0:
            print("No notes found in database for piece 1")
            return
        
        print(f"Testing with {min(len(notes_db), 3)} sample notes:")
        
        for i, note in enumerate(notes_db[:3]):
            piece_id = 1  # We know we're testing with piece 1
            voice = note['voice']
            onset = note['onset']
            expected_note_id = note['note_id']
            
            print(f"\n  Test {i+1}:")
            print(f"    Input: piece_id={piece_id}, voice={voice}, onset={onset}")
            print(f"    Expected note_id: {expected_note_id}")
            
            # Test the lookup
            found_note_id = updater.find_note_id(piece_id, voice, onset, tolerance=0.001)
            
            success = found_note_id == expected_note_id
            print(f"    Found note_id: {found_note_id}")
            print(f"    Result: {'✓ SUCCESS' if success else '✗ FAILED'}")
            
            if success:
                # Test with slight variation to check tolerance
                found_with_tolerance = updater.find_note_id(piece_id, voice, onset + 0.0005, tolerance=0.001)
                tolerance_success = found_with_tolerance == expected_note_id
                print(f"    Tolerance test (onset+0.0005): {'✓ SUCCESS' if tolerance_success else '✗ FAILED'}")
        
    except ImportError as e:
        print(f"Could not import NoteIdUpdater: {e}")
    except Exception as e:
        print(f"Error testing note ID lookup: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    print("MusicXML and Note Mapping Analysis Tool")
    print("=" * 50)
    
    # Test with piece 1 (you can change this)
    piece_id = 1
    
    # 1. Analyze MusicXML structure
    analyze_musicxml_structure(piece_id)
    
    # 2. Create test mapping data
    create_test_mapping_data(piece_id)
    
    # 3. Test note_id lookup functionality
    test_note_id_lookup()
    
    print(f"\n{'='*50}")
    print("Analysis complete!")
    
    print(f"\nNext steps for frontend implementation:")
    print("1. Load note positions from database for the selected piece")
    print("2. When a note is clicked in Verovio SVG, extract its position/order")
    print("3. Use position information to find corresponding database note")
    print("4. Call API to get detailed note information")

if __name__ == "__main__":
    main()
