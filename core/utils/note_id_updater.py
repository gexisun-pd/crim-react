"""
Utility module for updating note_id fields in analysis tables.

This module provides functions to find and populate note_id references
in melodic_intervals, melodic_ngrams, and melodic_entries tables by
matching piece_id, voice, and onset values with the notes table.
"""

import sqlite3
import os
import sys
from typing import List, Dict, Optional, Tuple

# Add the core directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db.db import PiecesDB


class NoteIdUpdater:
    """Class for updating note_id fields in analysis tables."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the NoteIdUpdater with database path."""
        if db_path is None:
            # Get project root directory (three levels up from core/utils/)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(project_root, 'database', 'analysis.db')
        self.db_path = db_path
    
    def find_note_id(self, piece_id: int, voice: int, onset: float, 
                    tolerance: float = 0.001, cursor=None) -> Optional[int]:
        """
        Find note_id by matching piece_id, voice, and onset in notes table.
        
        Args:
            piece_id: The piece ID to match
            voice: The voice number to match  
            onset: The onset time to match
            tolerance: Tolerance for floating point comparison of onset
            cursor: Optional database cursor to reuse
            
        Returns:
            The note_id if found, None otherwise
        """
        should_close = False
        try:
            if cursor is None:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                should_close = True
            
            # Query with tolerance for floating point comparison
            cursor.execute("""
                SELECT note_id FROM notes 
                WHERE piece_id = ? AND voice = ? 
                AND ABS(onset - ?) <= ?
                ORDER BY ABS(onset - ?) ASC
                LIMIT 1
            """, (piece_id, voice, onset, tolerance, onset))
            
            result = cursor.fetchone()
            
            if should_close:
                conn.close()
            
            return result[0] if result else None
            
        except sqlite3.Error as e:
            print(f"Database error finding note_id: {e}")
            if should_close and 'conn' in locals():
                conn.close()
            return None
    
    def find_note_ids_batch(self, records: List[Dict], tolerance: float = 0.001) -> Dict[Tuple, int]:
        """
        Find note_ids for a batch of records efficiently.
        
        Args:
            records: List of dicts with 'piece_id', 'voice', 'onset' keys
            tolerance: Tolerance for floating point comparison
            
        Returns:
            Dictionary mapping (piece_id, voice, onset) tuples to note_ids
        """
        note_id_map = {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create a set of unique lookup keys to avoid duplicates
            unique_keys = set()
            for record in records:
                key = (record['piece_id'], record['voice'], record['onset'])
                unique_keys.add(key)
            
            # Batch lookup
            for piece_id, voice, onset in unique_keys:
                cursor.execute("""
                    SELECT note_id FROM notes 
                    WHERE piece_id = ? AND voice = ? 
                    AND ABS(onset - ?) <= ?
                    ORDER BY ABS(onset - ?) ASC
                    LIMIT 1
                """, (piece_id, voice, onset, tolerance, onset))
                
                result = cursor.fetchone()
                if result:
                    note_id_map[(piece_id, voice, onset)] = result[0]
            
            conn.close()
            return note_id_map
            
        except sqlite3.Error as e:
            print(f"Database error in batch note_id lookup: {e}")
            if 'conn' in locals():
                conn.close()
            return {}
    
    def update_melodic_intervals_note_ids(self, piece_id: Optional[int] = None,
                                        tolerance: float = 0.001) -> int:
        """
        Update note_id field in melodic_intervals table.
        
        Args:
            piece_id: If provided, only update records for this piece
            tolerance: Tolerance for onset matching
            
        Returns:
            Number of records updated
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get records that need note_id updates
            where_clause = "WHERE note_id IS NULL"
            params = []
            
            if piece_id is not None:
                where_clause += " AND piece_id = ?"
                params.append(piece_id)
            
            cursor.execute(f"""
                SELECT interval_id, piece_id, voice, onset 
                FROM melodic_intervals 
                {where_clause}
            """, params)
            
            records = cursor.fetchall()
            updated_count = 0
            
            print(f"Found {len(records)} melodic_intervals records to update note_id")
            
            if len(records) == 0:
                conn.close()
                return 0
            
            # Show progress for large datasets
            total_records = len(records)
            progress_interval = max(1, total_records // 20)  # Show progress every 5%
            
            # Update each record
            for i, (interval_id, pid, voice, onset) in enumerate(records):
                # Show progress
                if i % progress_interval == 0 or i == total_records - 1:
                    progress = (i + 1) / total_records * 100
                    print(f"  Progress: {i+1}/{total_records} ({progress:.1f}%) - Updated: {updated_count}")
                
                note_id = self.find_note_id(pid, voice, onset, tolerance)
                if note_id:
                    cursor.execute("""
                        UPDATE melodic_intervals 
                        SET note_id = ? 
                        WHERE interval_id = ?
                    """, (note_id, interval_id))
                    updated_count += 1
                else:
                    if updated_count < 10:  # Only show first few warnings
                        print(f"    Warning: No note found for melodic_interval {interval_id} "
                              f"(piece_id={pid}, voice={voice}, onset={onset})")
                    elif updated_count == 10:
                        print(f"    ... (suppressing further warnings)")
            
            conn.commit()
            conn.close()
            
            print(f"Updated note_id for {updated_count} melodic_intervals records")
            return updated_count
            
        except sqlite3.Error as e:
            print(f"Database error updating melodic_intervals note_ids: {e}")
            if 'conn' in locals():
                conn.close()
            return 0
    
    def update_melodic_ngrams_note_ids(self, piece_id: Optional[int] = None,
                                     tolerance: float = 0.001) -> int:
        """
        Update note_id field in melodic_ngrams table.
        
        Args:
            piece_id: If provided, only update records for this piece
            tolerance: Tolerance for onset matching
            
        Returns:
            Number of records updated
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get records that need note_id updates
            where_clause = "WHERE note_id IS NULL"
            params = []
            
            if piece_id is not None:
                where_clause += " AND piece_id = ?"
                params.append(piece_id)
            
            cursor.execute(f"""
                SELECT ngram_id, piece_id, voice, onset 
                FROM melodic_ngrams 
                {where_clause}
            """, params)
            
            records = cursor.fetchall()
            updated_count = 0
            
            print(f"Found {len(records)} melodic_ngrams records to update note_id")
            
            if len(records) == 0:
                conn.close()
                return 0
            
            # Show progress for large datasets
            total_records = len(records)
            progress_interval = max(1, total_records // 20)  # Show progress every 5%
            
            # Update each record
            for i, (ngram_id, pid, voice, onset) in enumerate(records):
                # Show progress
                if i % progress_interval == 0 or i == total_records - 1:
                    progress = (i + 1) / total_records * 100
                    print(f"  Progress: {i+1}/{total_records} ({progress:.1f}%) - Updated: {updated_count}")
                
                note_id = self.find_note_id(pid, voice, onset, tolerance)
                if note_id:
                    cursor.execute("""
                        UPDATE melodic_ngrams 
                        SET note_id = ? 
                        WHERE ngram_id = ?
                    """, (note_id, ngram_id))
                    updated_count += 1
                else:
                    if updated_count < 10:  # Only show first few warnings
                        print(f"    Warning: No note found for melodic_ngram {ngram_id} "
                              f"(piece_id={pid}, voice={voice}, onset={onset})")
                    elif updated_count == 10:
                        print(f"    ... (suppressing further warnings)")
            
            conn.commit()
            conn.close()
            
            print(f"Updated note_id for {updated_count} melodic_ngrams records")
            return updated_count
            
        except sqlite3.Error as e:
            print(f"Database error updating melodic_ngrams note_ids: {e}")
            if 'conn' in locals():
                conn.close()
            return 0
    
    def update_melodic_entries_note_ids(self, piece_id: Optional[int] = None,
                                      tolerance: float = 0.001) -> int:
        """
        Update note_id field in melodic_entries table.
        
        Args:
            piece_id: If provided, only update records for this piece
            tolerance: Tolerance for onset matching
            
        Returns:
            Number of records updated
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
            cursor = conn.cursor()
            
            # Get records that need note_id updates
            where_clause = "WHERE note_id IS NULL"
            params = []
            
            if piece_id is not None:
                where_clause += " AND piece_id = ?"
                params.append(piece_id)
            
            cursor.execute(f"""
                SELECT entry_id, piece_id, voice, onset 
                FROM melodic_entries 
                {where_clause}
            """, params)
            
            records = cursor.fetchall()
            updated_count = 0
            failed_count = 0
            
            print(f"Found {len(records)} melodic_entries records to update note_id")
            
            if len(records) == 0:
                conn.close()
                return 0
            
            # Show progress for large datasets
            total_records = len(records)
            progress_interval = max(1, total_records // 20)  # Show progress every 5%
            
            # Process in smaller batches to avoid locking issues
            batch_size = 100
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                batch_updated = 0
                
                # Start a transaction for this batch
                conn.execute("BEGIN IMMEDIATE")
                
                try:
                    for j, (entry_id, pid, voice, onset) in enumerate(batch):
                        # Show progress
                        current_idx = i + j
                        if current_idx % progress_interval == 0 or current_idx == total_records - 1:
                            progress = (current_idx + 1) / total_records * 100
                            print(f"  Progress: {current_idx+1}/{total_records} ({progress:.1f}%) - Updated: {updated_count}, Failed: {failed_count}")
                        
                        note_id = self.find_note_id(pid, voice, onset, tolerance, cursor)
                        if note_id:
                            cursor.execute("""
                                UPDATE melodic_entries 
                                SET note_id = ? 
                                WHERE entry_id = ?
                            """, (note_id, entry_id))
                            batch_updated += 1
                        else:
                            failed_count += 1
                            if failed_count <= 5:  # Only show first few warnings
                                print(f"    Warning: No note found for melodic_entry {entry_id} "
                                      f"(piece_id={pid}, voice={voice}, onset={onset})")
                            elif failed_count == 6:
                                print(f"    ... (suppressing further warnings)")
                    
                    # Commit the batch
                    conn.commit()
                    updated_count += batch_updated
                    
                except sqlite3.Error as e:
                    print(f"Error processing batch starting at {i}: {e}")
                    conn.rollback()
                    break
            
            conn.close()
            
            print(f"Updated note_id for {updated_count} melodic_entries records")
            if failed_count > 0:
                print(f"Failed to find note_id for {failed_count} records")
            return updated_count
            
        except sqlite3.Error as e:
            print(f"Database error updating melodic_entries note_ids: {e}")
            if 'conn' in locals():
                conn.close()
            return 0
    
    def update_all_note_ids(self, piece_id: Optional[int] = None, 
                          tolerance: float = 0.001) -> Dict[str, int]:
        """
        Update note_id fields in all three analysis tables.
        
        Args:
            piece_id: If provided, only update records for this piece
            tolerance: Tolerance for onset matching
            
        Returns:
            Dictionary with update counts for each table
        """
        results = {}
        
        print("=== Updating note_id fields in all analysis tables ===")
        
        # Update melodic_intervals
        print("\n--- Updating melodic_intervals ---")
        results['melodic_intervals'] = self.update_melodic_intervals_note_ids(piece_id, tolerance)
        
        # Update melodic_ngrams  
        print("\n--- Updating melodic_ngrams ---")
        results['melodic_ngrams'] = self.update_melodic_ngrams_note_ids(piece_id, tolerance)
        
        # Update melodic_entries
        print("\n--- Updating melodic_entries ---")
        results['melodic_entries'] = self.update_melodic_entries_note_ids(piece_id, tolerance)
        
        print(f"\n=== Summary ===")
        total_updated = sum(results.values())
        for table, count in results.items():
            print(f"{table}: {count} records updated")
        print(f"Total: {total_updated} records updated")
        
        return results
    
    def add_note_id_columns_to_existing_tables(self):
        """
        Add note_id columns to existing tables if they don't exist.
        This is useful for migrating existing databases.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check and add note_id column to melodic_intervals
            cursor.execute("PRAGMA table_info(melodic_intervals)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'note_id' not in columns:
                print("Adding note_id column to melodic_intervals table...")
                cursor.execute("""
                    ALTER TABLE melodic_intervals 
                    ADD COLUMN note_id INTEGER REFERENCES notes(note_id) ON DELETE CASCADE
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_melodic_intervals_note 
                    ON melodic_intervals(note_id)
                """)
            
            # Check and add note_id column to melodic_ngrams
            cursor.execute("PRAGMA table_info(melodic_ngrams)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'note_id' not in columns:
                print("Adding note_id column to melodic_ngrams table...")
                cursor.execute("""
                    ALTER TABLE melodic_ngrams 
                    ADD COLUMN note_id INTEGER REFERENCES notes(note_id) ON DELETE CASCADE
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_melodic_ngrams_note 
                    ON melodic_ngrams(note_id)
                """)
            
            # Check and add note_id column to melodic_entries
            cursor.execute("PRAGMA table_info(melodic_entries)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'note_id' not in columns:
                print("Adding note_id column to melodic_entries table...")
                cursor.execute("""
                    ALTER TABLE melodic_entries 
                    ADD COLUMN note_id INTEGER REFERENCES notes(note_id) ON DELETE CASCADE
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_melodic_entries_note 
                    ON melodic_entries(note_id)
                """)
            
            conn.commit()
            conn.close()
            print("Successfully added note_id columns to existing tables")
            
        except sqlite3.Error as e:
            print(f"Database error adding note_id columns: {e}")
            if 'conn' in locals():
                conn.close()
            raise

    def test_note_id_functionality(self, create_test_data: bool = False) -> Dict[str, any]:
        """
        Test the note_id functionality with sample data.
        
        Args:
            create_test_data: If True, create some test data first
            
        Returns:
            Dictionary with test results and statistics
        """
        results = {
            'database_exists': False,
            'tables_exist': {},
            'sample_counts': {},
            'test_results': {},
            'errors': []
        }
        
        print("=== Testing Note ID Functionality ===")
        
        # Check if database exists
        if os.path.exists(self.db_path):
            results['database_exists'] = True
            print(f"✓ Database exists: {self.db_path}")
        else:
            results['errors'].append(f"Database not found: {self.db_path}")
            print(f"✗ Database not found: {self.db_path}")
            return results
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check which tables exist
            tables_to_check = ['pieces', 'notes', 'melodic_intervals', 'melodic_ngrams', 'melodic_entries']
            for table in tables_to_check:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                exists = cursor.fetchone() is not None
                results['tables_exist'][table] = exists
                print(f"{'✓' if exists else '✗'} Table '{table}' {'exists' if exists else 'missing'}")
            
            # Get sample counts from each table
            for table in tables_to_check:
                if results['tables_exist'][table]:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        results['sample_counts'][table] = count
                        print(f"  - {table}: {count} records")
                    except sqlite3.Error as e:
                        results['errors'].append(f"Error counting {table}: {e}")
                        print(f"  - {table}: Error counting - {e}")
            
            # Create test data if requested
            if create_test_data:
                print("\n--- Creating Test Data ---")
                test_data_results = self._create_test_data(cursor)
                results['test_data_creation'] = test_data_results
            
            # Test note_id lookup functionality
            if results['sample_counts'].get('notes', 0) > 0:
                print("\n--- Testing Note ID Lookup ---")
                
                # Get a sample note to test with
                cursor.execute("SELECT piece_id, voice, onset, note_id FROM notes LIMIT 1")
                sample_note = cursor.fetchone()
                
                if sample_note:
                    piece_id, voice, onset, expected_note_id = sample_note
                    print(f"Testing with sample: piece_id={piece_id}, voice={voice}, onset={onset}")
                    
                    # Test find_note_id function
                    found_note_id = self.find_note_id(piece_id, voice, onset)
                    success = found_note_id == expected_note_id
                    results['test_results']['note_lookup'] = {
                        'expected': expected_note_id,
                        'found': found_note_id,
                        'success': success
                    }
                    print(f"{'✓' if success else '✗'} Note lookup: expected {expected_note_id}, found {found_note_id}")
                    
                    # Test with slight tolerance
                    found_with_tolerance = self.find_note_id(piece_id, voice, onset + 0.0005, tolerance=0.001)
                    tolerance_success = found_with_tolerance == expected_note_id
                    results['test_results']['tolerance_lookup'] = {
                        'expected': expected_note_id,
                        'found': found_with_tolerance,
                        'success': tolerance_success
                    }
                    print(f"{'✓' if tolerance_success else '✗'} Tolerance lookup: expected {expected_note_id}, found {found_with_tolerance}")
            
            # Test batch lookup if we have multiple notes
            if results['sample_counts'].get('notes', 0) > 1:
                print("\n--- Testing Batch Note ID Lookup ---")
                
                cursor.execute("SELECT piece_id, voice, onset, note_id FROM notes LIMIT 3")
                sample_notes = cursor.fetchall()
                
                test_records = []
                expected_map = {}
                for piece_id, voice, onset, note_id in sample_notes:
                    test_records.append({'piece_id': piece_id, 'voice': voice, 'onset': onset})
                    expected_map[(piece_id, voice, onset)] = note_id
                
                found_map = self.find_note_ids_batch(test_records)
                batch_success = all(
                    found_map.get(key) == expected_map[key] 
                    for key in expected_map.keys()
                )
                
                results['test_results']['batch_lookup'] = {
                    'expected_count': len(expected_map),
                    'found_count': len(found_map),
                    'success': batch_success
                }
                print(f"{'✓' if batch_success else '✗'} Batch lookup: {len(found_map)}/{len(expected_map)} records found")
            
            # Test table structure for note_id columns
            print("\n--- Testing Table Structures ---")
            analysis_tables = ['melodic_intervals', 'melodic_ngrams', 'melodic_entries']
            
            for table in analysis_tables:
                if results['tables_exist'][table]:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [col[1] for col in cursor.fetchall()]
                    has_note_id = 'note_id' in columns
                    results['test_results'][f'{table}_has_note_id'] = has_note_id
                    print(f"{'✓' if has_note_id else '✗'} {table} has note_id column")
            
            conn.close()
            
        except sqlite3.Error as e:
            results['errors'].append(f"Database error during testing: {e}")
            print(f"✗ Database error: {e}")
            if 'conn' in locals():
                conn.close()
        
        # Print summary
        print(f"\n=== Test Summary ===")
        print(f"Database exists: {results['database_exists']}")
        print(f"Tables exist: {sum(results['tables_exist'].values())}/{len(results['tables_exist'])}")
        print(f"Test results: {len([r for r in results['test_results'].values() if isinstance(r, dict) and r.get('success')])}/{len(results['test_results'])} passed")
        if results['errors']:
            print(f"Errors encountered: {len(results['errors'])}")
            for error in results['errors']:
                print(f"  - {error}")
        
        return results
    
    def _create_test_data(self, cursor) -> Dict[str, any]:
        """Create minimal test data for testing note_id functionality."""
        results = {'created': {}, 'errors': []}
        
        try:
            # Create a test piece if none exists
            cursor.execute("SELECT COUNT(*) FROM pieces")
            pieces_count = cursor.fetchone()[0]
            
            if pieces_count == 0:
                print("Creating test piece...")
                cursor.execute("""
                    INSERT INTO pieces (path, filename, title, composer) 
                    VALUES (?, ?, ?, ?)
                """, ('/test/path', 'test_piece.xml', 'Test Piece', 'Test Composer'))
                piece_id = cursor.lastrowid
                results['created']['piece'] = piece_id
                print(f"Created test piece with ID: {piece_id}")
            else:
                cursor.execute("SELECT piece_id FROM pieces LIMIT 1")
                piece_id = cursor.fetchone()[0]
                print(f"Using existing piece ID: {piece_id}")
            
            # Create test notes if none exist for this piece
            cursor.execute("SELECT COUNT(*) FROM notes WHERE piece_id = ?", (piece_id,))
            notes_count = cursor.fetchone()[0]
            
            if notes_count == 0:
                print("Creating test notes...")
                # Get a note_set_id
                cursor.execute("SELECT set_id FROM note_sets LIMIT 1")
                note_set_result = cursor.fetchone()
                if not note_set_result:
                    results['errors'].append("No note_sets found - run init_db.py first")
                    return results
                
                note_set_id = note_set_result[0]
                
                # Create sample notes
                test_notes = [
                    (piece_id, note_set_id, 1, 'Voice1', 0.0, 1.0, 1.0, 1, 0.0, 60, 'C4', 'C', 4, 0, 'Note', 1, None),
                    (piece_id, note_set_id, 1, 'Voice1', 1.0, 1.0, 2.0, 1, 1.0, 62, 'D4', 'D', 4, 0, 'Note', 1, None),
                    (piece_id, note_set_id, 1, 'Voice1', 2.0, 1.0, 3.0, 1, 2.0, 64, 'E4', 'E', 4, 0, 'Note', 1, None),
                    (piece_id, note_set_id, 2, 'Voice2', 0.0, 2.0, 2.0, 1, 0.0, 55, 'G3', 'G', 3, 0, 'Note', 1, None),
                    (piece_id, note_set_id, 2, 'Voice2', 2.0, 1.0, 3.0, 1, 2.0, 57, 'A3', 'A', 3, 0, 'Note', 1, None),
                ]
                
                cursor.executemany("""
                    INSERT INTO notes (
                        piece_id, note_set_id, voice, voice_name, onset, duration, offset,
                        measure, beat, pitch, name, step, octave, `alter`, type, staff, tie
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, test_notes)
                
                results['created']['notes'] = len(test_notes)
                print(f"Created {len(test_notes)} test notes")
            
            # Create sample melodic_entries for testing if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='melodic_entries'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM melodic_entries WHERE piece_id = ?", (piece_id,))
                entries_count = cursor.fetchone()[0]
                
                if entries_count == 0:
                    # Get a melodic_ngram_set_id
                    cursor.execute("SELECT set_id FROM melodic_ngram_sets WHERE ngrams_entry = 1 LIMIT 1")
                    ngram_set_result = cursor.fetchone()
                    if ngram_set_result:
                        ngram_set_id = ngram_set_result[0]
                        
                        print("Creating test melodic entries...")
                        test_entries = [
                            (piece_id, ngram_set_id, None, 1, 'Voice1', 0.0, 'M2,M2', 3, 0, 1),
                            (piece_id, ngram_set_id, None, 2, 'Voice2', 0.0, 'M2', 2, 0, 1),
                        ]
                        
                        cursor.executemany("""
                            INSERT INTO melodic_entries (
                                piece_id, melodic_ngram_set_id, note_id, voice, voice_name,
                                onset, entry_pattern, entry_length, is_thematic, from_rest
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, test_entries)
                        
                        results['created']['melodic_entries'] = len(test_entries)
                        print(f"Created {len(test_entries)} test melodic entries")
            
            cursor.connection.commit()
            
        except sqlite3.Error as e:
            results['errors'].append(f"Error creating test data: {e}")
            print(f"Error creating test data: {e}")
        
        return results


def main():
    """Main function for standalone execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update note_id fields in analysis tables')
    parser.add_argument('--piece-id', type=int, help='Update only records for specific piece_id')
    parser.add_argument('--tolerance', type=float, default=0.001, 
                       help='Tolerance for onset matching (default: 0.001)')
    parser.add_argument('--table', choices=['melodic_intervals', 'melodic_ngrams', 'melodic_entries', 'all'],
                       default='all', help='Which table(s) to update')
    parser.add_argument('--add-columns', action='store_true',
                       help='Add note_id columns to existing tables if missing')
    parser.add_argument('--test', action='store_true',
                       help='Run functionality tests')
    parser.add_argument('--create-test-data', action='store_true',
                       help='Create minimal test data during testing')
    
    args = parser.parse_args()
    
    updater = NoteIdUpdater()
    
    # Run tests if requested
    if args.test:
        print("Running note_id functionality tests...")
        test_results = updater.test_note_id_functionality(args.create_test_data)
        
        # Print detailed test results
        print(f"\n=== Detailed Test Results ===")
        for key, value in test_results.items():
            if key == 'test_results':
                print(f"{key}:")
                for test_name, test_result in value.items():
                    if isinstance(test_result, dict) and 'success' in test_result:
                        status = '✓ PASS' if test_result['success'] else '✗ FAIL'
                        print(f"  {test_name}: {status}")
                        if not test_result['success']:
                            print(f"    Expected: {test_result.get('expected', 'N/A')}")
                            print(f"    Found: {test_result.get('found', 'N/A')}")
                    else:
                        print(f"  {test_name}: {test_result}")
            elif key == 'tables_exist':
                print(f"{key}:")
                for table, exists in value.items():
                    print(f"  {table}: {'✓' if exists else '✗'}")
            elif key == 'sample_counts':
                print(f"{key}:")
                for table, count in value.items():
                    print(f"  {table}: {count}")
            else:
                print(f"{key}: {value}")
        
        return
    
    # Add columns if requested
    if args.add_columns:
        updater.add_note_id_columns_to_existing_tables()
    
    # Update note_ids
    if args.table == 'all':
        updater.update_all_note_ids(args.piece_id, args.tolerance)
    elif args.table == 'melodic_intervals':
        updater.update_melodic_intervals_note_ids(args.piece_id, args.tolerance)
    elif args.table == 'melodic_ngrams':
        updater.update_melodic_ngrams_note_ids(args.piece_id, args.tolerance)
    elif args.table == 'melodic_entries':
        updater.update_melodic_entries_note_ids(args.piece_id, args.tolerance)


def run_tests():
    """Convenience function for running tests programmatically."""
    updater = NoteIdUpdater()
    return updater.test_note_id_functionality(create_test_data=True)


if __name__ == "__main__":
    main()
