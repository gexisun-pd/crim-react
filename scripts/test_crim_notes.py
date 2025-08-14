#!/usr/bin/env python3
"""
Test script to verify CRIM intervals library usage for note extraction.
This script tests different approaches to extract notes without writing to database.
"""

import os
import sys
import pandas as pd

# Test CRIM intervals import
try:
    import crim_intervals
    print("✓ Successfully imported crim_intervals")
    
    # Try different import approaches
    try:
        from crim_intervals import CorpusBase
        print("✓ Successfully imported CorpusBase")
    except ImportError as e:
        print(f"✗ Failed to import CorpusBase: {e}")
    
    try:
        from crim_intervals import importScore
        print("✓ Successfully imported importScore")
    except ImportError as e:
        print(f"✗ Failed to import importScore: {e}")
    
    # Try to find ImportedPiece
    try:
        from crim_intervals.main_objs import ImportedPiece
        print("✓ Successfully imported ImportedPiece from main_objs")
    except ImportError:
        try:
            from crim_intervals import ImportedPiece
            print("✓ Successfully imported ImportedPiece directly")
        except ImportError:
            print("✗ Could not import ImportedPiece")
            ImportedPiece = None
    
except ImportError as e:
    print(f"✗ Failed to import crim_intervals: {e}")
    sys.exit(1)

def test_single_piece_approach():
    """Test extracting notes from a single piece using importScore"""
    print("\n=== Testing Single Piece Approach ===")
    
    # Get a test file
    project_root = os.path.dirname(os.path.dirname(__file__))
    test_file = os.path.join(project_root, 'data', 'test', 'Gabrieli_C001_Inclina_Domine_6vv.musicxml')
    
    if not os.path.exists(test_file):
        print(f"✗ Test file not found: {test_file}")
        return
    
    try:
        print(f"Importing piece: {os.path.basename(test_file)}")
        piece = importScore(test_file)
        print("✓ Successfully imported piece")
        
        # Try to get metadata
        try:
            metadata = piece.metadata
            print(f"✓ Metadata: {metadata}")
        except Exception as e:
            print(f"✗ Failed to get metadata: {e}")
        
        # Try to get notes
        try:
            notes_df = piece.notes()
            print(f"✓ Successfully extracted notes")
            print(f"  Notes DataFrame shape: {notes_df.shape}")
            print(f"  Columns: {list(notes_df.columns)}")
            
            if not notes_df.empty:
                print(f"  First few rows:")
                print(notes_df.head(3))
                
                # Check for actual data
                print(f"\n  Data types:")
                print(notes_df.dtypes)
                
                print(f"\n  Non-null counts:")
                print(notes_df.count())
            else:
                print("  ✗ Notes DataFrame is empty")
                
        except Exception as e:
            print(f"✗ Failed to extract notes: {e}")
            
    except Exception as e:
        print(f"✗ Failed to import piece: {e}")

def test_corpus_approach():
    """Test extracting notes using CorpusBase"""
    print("\n=== Testing Corpus Approach ===")
    
    # Get a test file
    project_root = os.path.dirname(os.path.dirname(__file__))
    test_file = os.path.join(project_root, 'data', 'test', 'Gabrieli_C001_Inclina_Domine_6vv.musicxml')
    
    if not os.path.exists(test_file):
        print(f"✗ Test file not found: {test_file}")
        return
    
    try:
        print(f"Creating corpus with: {os.path.basename(test_file)}")
        corpus = CorpusBase([test_file])
        print("✓ Successfully created corpus")
        
        # Explore corpus attributes
        print(f"Corpus attributes: {[attr for attr in dir(corpus) if not attr.startswith('_')]}")
        
        # Try different ways to access pieces
        if hasattr(corpus, 'scores'):
            print(f"✓ Corpus has scores attribute, length: {len(corpus.scores)}")
            if len(corpus.scores) > 0:
                piece = corpus.scores[0]
                print("✓ Successfully accessed piece from corpus.scores")
                
                # Try to get notes from the piece
                try:
                    notes_df = piece.notes()
                    print(f"✓ Successfully extracted notes from piece")
                    print(f"  Notes DataFrame shape: {notes_df.shape}")
                    
                    if not notes_df.empty:
                        print(f"  First few rows:")
                        print(notes_df.head(3))
                    else:
                        print("  ✗ Notes DataFrame is empty")
                        
                except Exception as e:
                    print(f"✗ Failed to extract notes from piece: {e}")
        
        # Try batch method if ImportedPiece is available
        if ImportedPiece:
            print("\nTrying batch method...")
            try:
                func = ImportedPiece.notes
                list_of_dfs = corpus.batch(func, metadata=True)
                print(f"✓ Successfully used batch method")
                print(f"  Number of DataFrames returned: {len(list_of_dfs)}")
                
                if list_of_dfs and len(list_of_dfs) > 0:
                    notes_df = list_of_dfs[0]
                    print(f"  First DataFrame shape: {notes_df.shape}")
                    
                    if not notes_df.empty:
                        print(f"  First few rows:")
                        print(notes_df.head(3))
                    else:
                        print("  ✗ First DataFrame is empty")
                else:
                    print("  ✗ No DataFrames returned from batch method")
                    
            except Exception as e:
                print(f"✗ Failed to use batch method: {e}")
        else:
            print("ImportedPiece not available, skipping batch method test")
            
    except Exception as e:
        print(f"✗ Failed to create corpus: {e}")

def test_module_exploration():
    """Explore the crim_intervals module to understand its structure"""
    print("\n=== Exploring CRIM Intervals Module ===")
    
    print("Available attributes in crim_intervals:")
    attrs = [attr for attr in dir(crim_intervals) if not attr.startswith('_')]
    for attr in attrs:
        print(f"  - {attr}")
    
    # Try to find functions related to notes
    print(f"\nLooking for 'notes' related functions:")
    notes_attrs = [attr for attr in attrs if 'note' in attr.lower()]
    if notes_attrs:
        for attr in notes_attrs:
            print(f"  - {attr}")
    else:
        print("  No 'notes' related attributes found")

def main():
    """Run all tests"""
    print("=== CRIM Intervals Test Script ===")
    
    test_module_exploration()
    test_single_piece_approach()
    test_corpus_approach()
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()
