import xml.etree.ElementTree as ET
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
from db.db import PiecesDB

def analyze_musicxml_structure(file_path):
    """Analyze MusicXML file structure to check for xml:id attributes"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        print(f"\n=== Analyzing {os.path.basename(file_path)} ===")
        print(f"Root element: {root.tag}")
        
        # Check for xml:id attributes in note elements
        notes_with_id = root.findall('.//note[@xml:id]', {'xml': 'http://www.w3.org/XML/1998/namespace'})
        notes_without_id = root.findall('.//note')
        
        print(f"Total notes: {len(notes_without_id)}")
        print(f"Notes with xml:id: {len(notes_with_id)}")
        
        if notes_with_id:
            print("\nFirst 5 notes with xml:id:")
            for i, note in enumerate(notes_with_id[:5]):
                xml_id = note.get('{http://www.w3.org/XML/1998/namespace}id')
                print(f"  Note {i+1}: xml:id='{xml_id}'")
        
        # Check for other elements with xml:id
        all_with_id = root.findall('.//*[@xml:id]', {'xml': 'http://www.w3.org/XML/1998/namespace'})
        print(f"Total elements with xml:id: {len(all_with_id)}")
        
        return {
            'total_notes': len(notes_without_id),
            'notes_with_id': len(notes_with_id),
            'total_elements_with_id': len(all_with_id),
            'has_note_ids': len(notes_with_id) > 0
        }
        
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return None

def main():
    """Check MusicXML structure for all pieces in database"""
    db = PiecesDB()
    pieces = db.get_all_pieces()
    
    results = []
    
    for piece in pieces[:3]:  # Check first 3 pieces
        file_path = piece.get('path')
        if file_path:
            # Convert to absolute path
            if not os.path.isabs(file_path):
                base_path = os.path.join(os.path.dirname(__file__), '..', 'data')
                file_path = os.path.join(base_path, file_path)
            
            if os.path.exists(file_path):
                result = analyze_musicxml_structure(file_path)
                if result:
                    result['piece_id'] = piece['piece_id']
                    result['filename'] = piece['filename']
                    results.append(result)
    
    print(f"\n=== Summary ===")
    for result in results:
        print(f"Piece {result['piece_id']} ({result['filename']}): "
              f"{'HAS' if result['has_note_ids'] else 'NO'} note xml:id attributes")

if __name__ == "__main__":
    main()