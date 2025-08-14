import os
import hashlib
from datetime import datetime
from typing import List, Dict
import sys

# Add the core directory to the path to import db module
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db.db import PiecesDB

# Import crim_intervals for metadata extraction
try:
    import crim_intervals
    from crim_intervals import importScore
    CRIM_INTERVALS_AVAILABLE = True
except ImportError:
    print("Warning: crim_intervals not available. Falling back to filename-based extraction.")
    CRIM_INTERVALS_AVAILABLE = False

def calculate_sha256(file_path: str) -> str:
    """Calculate SHA256 hash of a file"""
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error calculating SHA256 for {file_path}: {e}")
        return None

def extract_title(file_path: str) -> str:
    """Extract title from file using crim_intervals metadata or filename fallback"""
    if CRIM_INTERVALS_AVAILABLE:
        try:
            # Use crim_intervals to get metadata
            piece = importScore(file_path)
            metadata = piece.metadata
            
            # Try to get title from metadata
            if 'title' in metadata and metadata['title']:
                return metadata['title']
            elif 'movementName' in metadata and metadata['movementName']:
                return metadata['movementName']
            elif 'workTitle' in metadata and metadata['workTitle']:
                return metadata['workTitle']
        except Exception as e:
            print(f"Warning: Could not extract title from {file_path} using crim_intervals: {e}")
    
    # Fallback to filename-based extraction
    filename = os.path.basename(file_path)
    title = os.path.splitext(filename)[0]
    
    # Remove .xml if it's a .musicxml.xml file
    if title.endswith('.musicxml'):
        title = title[:-9]
    
    # Replace underscores with spaces and clean up
    title = title.replace('_', ' ')
    return title

def extract_composer(file_path: str) -> str:
    """Extract composer from file using crim_intervals metadata or filename fallback"""
    if CRIM_INTERVALS_AVAILABLE:
        try:
            # Use crim_intervals to get metadata
            piece = importScore(file_path)
            metadata = piece.metadata
            
            # Try to get composer from metadata
            if 'composer' in metadata and metadata['composer']:
                return metadata['composer']
            elif 'creators' in metadata and metadata['creators']:
                # Handle multiple creators if needed
                creators = metadata['creators']
                if isinstance(creators, list) and len(creators) > 0:
                    return creators[0]
                elif isinstance(creators, str):
                    return creators
        except Exception as e:
            print(f"Warning: Could not extract composer from {file_path} using crim_intervals: {e}")
    
    # Fallback to filename-based extraction
    filename = os.path.basename(file_path)
    
    # Try to extract composer from filename pattern
    if '_' in filename:
        parts = filename.split('_')
        # Assume first part might be composer
        composer = parts[0]
        return composer
    
    return "Unknown"

def get_musicxml_files(directory: str) -> List[str]:
    """Get all .musicxml and .musicxml.xml files from directory"""
    musicxml_files = []
    
    try:
        for filename in os.listdir(directory):
            if filename.endswith('.musicxml') or filename.endswith('.musicxml.xml'):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    musicxml_files.append(file_path)
        
        print(f"Found {len(musicxml_files)} MusicXML files in {directory}")
        return musicxml_files
        
    except Exception as e:
        print(f"Error reading directory {directory}: {e}")
        return []

def process_piece(file_path: str, data_root: str) -> Dict:
    """Process a single piece file and return data dict"""
    try:
        # Calculate relative path from data directory
        rel_path = os.path.relpath(file_path, data_root)
        
        piece_data = {
            'path': rel_path,
            'filename': os.path.basename(file_path),
            'title': extract_title(file_path),
            'composer': extract_composer(file_path),
            'sha256': calculate_sha256(file_path)
        }
        
        return piece_data
        
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None

def ingest_pieces_from_directory(test_dir: str = None):
    """Main function to ingest pieces from data/test directory"""
    
    # Get project root directory (two levels up from core/ingest/)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    if test_dir is None:
        test_dir = os.path.join(project_root, 'data', 'test')
    
    data_root = os.path.join(project_root, 'data')
    
    print(f"Scanning directory: {test_dir}")
    print(f"Data root: {data_root}")
    
    # Check if directory exists
    if not os.path.exists(test_dir):
        print(f"Error: Directory {test_dir} does not exist")
        return
    
    # Get all MusicXML files
    musicxml_files = get_musicxml_files(test_dir)
    
    if not musicxml_files:
        print("No MusicXML files found")
        return
    
    # Initialize database connection
    db = PiecesDB()
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    # Process each file
    for file_path in musicxml_files:
        try:
            print(f"Processing: {os.path.basename(file_path)}")
            
            # Process the piece
            piece_data = process_piece(file_path, data_root)
            
            if piece_data is None:
                error_count += 1
                continue
            
            # Check if piece already exists
            if db.piece_exists(piece_data['path'], piece_data['filename']):
                print(f"Skipping {piece_data['filename']} - already exists in database")
                skipped_count += 1
                continue
            
            # Insert into database
            piece_id = db.insert_piece(piece_data)
            
            if piece_id:
                processed_count += 1
            else:
                error_count += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            error_count += 1
            continue
    
    # Print summary
    print(f"\n=== Ingestion Summary ===")
    print(f"Total files found: {len(musicxml_files)}")
    print(f"Successfully processed: {processed_count}")
    print(f"Skipped (already exists): {skipped_count}")
    print(f"Errors: {error_count}")

if __name__ == "__main__":
    ingest_pieces_from_directory()