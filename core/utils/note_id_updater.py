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
        Update note_id field in melodic_intervals table using optimized batch method.
        
        Args:
            piece_id: If provided, only update records for this piece
            tolerance: Tolerance for onset matching
            
        Returns:
            Number of records updated
        """
        return self.update_note_ids_batch_optimized('melodic_intervals', piece_id, tolerance)
    
    def update_melodic_ngrams_note_ids(self, piece_id: Optional[int] = None,
                                     tolerance: float = 0.001) -> int:
        """
        Update note_id field in melodic_ngrams table using optimized batch method.
        
        Args:
            piece_id: If provided, only update records for this piece
            tolerance: Tolerance for onset matching
            
        Returns:
            Number of records updated
        """
        return self.update_note_ids_batch_optimized('melodic_ngrams', piece_id, tolerance)
    
    def update_melodic_entries_note_ids(self, piece_id: Optional[int] = None,
                                      tolerance: float = 0.001) -> int:
        """
        Update note_id field in melodic_entries table using optimized batch method.
        
        Args:
            piece_id: If provided, only update records for this piece
            tolerance: Tolerance for onset matching
            
        Returns:
            Number of records updated
        """
        return self.update_note_ids_batch_optimized('melodic_entries', piece_id, tolerance)
    
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
    
    def ensure_optimal_indexes(self):
        """
        Create optimal indexes for note_id lookup performance.
        This is the most critical optimization.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            print("=== Creating Optimal Indexes for Note ID Lookup ===")
            
            # 1) Critical: Composite index on notes table for JOIN performance
            print("Creating composite index on notes(piece_id, voice, onset)...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_lookup 
                ON notes(piece_id, voice, onset)
            """)
            
            # 2) Additional useful indexes for notes table
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_piece_voice 
                ON notes(piece_id, voice)
            """)
            
            # 3) Ensure analysis tables have indexes for JOIN operations
            analysis_tables = ['melodic_intervals', 'melodic_ngrams', 'melodic_entries']
            
            for table in analysis_tables:
                # Check if table exists first
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    print(f"Creating lookup index on {table}(piece_id, voice, onset)...")
                    cursor.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{table}_lookup 
                        ON {table}(piece_id, voice, onset)
                    """)
            
            conn.commit()
            conn.close()
            
            print("✓ Optimal indexes created successfully")
            
        except sqlite3.Error as e:
            print(f"Error creating indexes: {e}")
            if 'conn' in locals():
                conn.close()
            raise
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
    
    def update_note_ids_batch_optimized(self, table_name: str, piece_id: Optional[int] = None,
                                      tolerance: float = 0.001, batch_size: int = 5000) -> int:
        """
        Optimized batch update using JOIN and temporary tables.
        This is the main method for updating note_id fields efficiently.
        
        Args:
            table_name: Name of the table to update ('melodic_intervals', 'melodic_ngrams', 'melodic_entries')
            piece_id: If provided, only update records for this piece
            tolerance: Tolerance for onset matching (default: 0.001)
            batch_size: Process records in batches of this size for large datasets (default: 5000)
            
        Returns:
            Number of records updated
        """
        if table_name not in ['melodic_intervals', 'melodic_ngrams', 'melodic_entries']:
            raise ValueError(f"Invalid table name: {table_name}")
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL") 
            conn.execute("PRAGMA cache_size=10000")
            cursor = conn.cursor()
            
            # Get the primary key column name for the table
            pk_map = {
                'melodic_intervals': 'interval_id',
                'melodic_ngrams': 'ngram_id', 
                'melodic_entries': 'entry_id'
            }
            pk_column = pk_map[table_name]
            
            print(f"=== Updating {table_name} ===")
            
            # Ensure optimal indexes exist
            self.ensure_optimal_indexes()
            
            # Count records that need updating
            where_clause = "WHERE note_id IS NULL"
            params = []
            if piece_id is not None:
                where_clause += " AND piece_id = ?"
                params.append(piece_id)
            
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} {where_clause}", params)
            total_count = cursor.fetchone()[0]
            
            if total_count == 0:
                print(f"No records in {table_name} need note_id updates")
                conn.close()
                return 0
            
            print(f"Found {total_count} records to update in {table_name}")
            
            # Choose update strategy based on dataset size
            if total_count > batch_size:
                return self._update_in_batches(cursor, table_name, pk_column, piece_id, tolerance, total_count, batch_size)
            else:
                return self._update_all_at_once(cursor, table_name, pk_column, piece_id, tolerance, total_count)
                
        except sqlite3.Error as e:
            print(f"Database error in batch update: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return 0
    
    def _update_all_at_once(self, cursor, table_name: str, pk_column: str, 
                           piece_id: Optional[int], tolerance: float, total_count: int) -> int:
        """Update all records at once using temporary table approach."""
        
        # Method 1: Using temporary table approach for better compatibility
        print("Creating temporary mapping table...")
        
        # Show progress for large datasets
        if total_count > 1000:
            print(f"  Processing {total_count} records (this may take a while)...")
        
        # Create a temporary table with the mapping
        cursor.execute("""
            DROP TABLE IF EXISTS temp_note_mapping
        """)
        
        print("  Building note_id mapping...")
        
        # Build the query and parameters correctly
        temp_query = f"""
            CREATE TEMP TABLE temp_note_mapping AS
            SELECT 
                t.{pk_column} as target_id,
                n.note_id as matched_note_id
            FROM {table_name} t
            LEFT JOIN notes n ON (
                n.piece_id = t.piece_id 
                AND n.voice = t.voice 
                AND ABS(n.onset - t.onset) <= ?
            )
            WHERE t.note_id IS NULL
        """
        
        if piece_id is not None:
            temp_query += " AND t.piece_id = ?"
            temp_params = [tolerance, piece_id]
        else:
            temp_params = [tolerance]
        
        cursor.execute(temp_query, temp_params)
        print("  Mapping table created successfully")
        
        # Count successful mappings
        cursor.execute("SELECT COUNT(*) FROM temp_note_mapping WHERE matched_note_id IS NOT NULL")
        mapped_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM temp_note_mapping WHERE matched_note_id IS NULL")
        unmapped_count = cursor.fetchone()[0]
        
        print(f"  Found matches for {mapped_count}/{total_count} records")
        if unmapped_count > 0:
            print(f"  Warning: {unmapped_count} records could not be matched")
        
        # Update using the mapping table with progress monitoring
        print("  Applying updates...")
        
        # For large datasets, we can't easily show real-time progress during UPDATE,
        # but we can estimate timing
        import time
        start_time = time.time()
        
        # Enable progress monitoring in SQLite if possible
        if total_count > 10000:
            print(f"  Updating {mapped_count} records (this may take several minutes)...")
            print("  Please wait - SQLite is processing the batch update...")
        
        cursor.execute(f"""
            UPDATE {table_name}
            SET note_id = (
                SELECT matched_note_id 
                FROM temp_note_mapping 
                WHERE target_id = {table_name}.{pk_column}
            )
            WHERE {pk_column} IN (
                SELECT target_id 
                FROM temp_note_mapping 
                WHERE matched_note_id IS NOT NULL
            )
        """)
        
        direct_updated = cursor.rowcount
        elapsed = time.time() - start_time
        
        if elapsed > 1:  # Only show timing for operations that took more than 1 second
            print(f"  Database update completed in {elapsed:.1f} seconds: {direct_updated} records updated")
        else:
            print(f"  Database update completed: {direct_updated} records updated")
        
        print(f"Direct JOIN update completed: {direct_updated} records updated")
        
        # Check for remaining unmatched records
        print("  Verifying update results...")
        remaining_query = f"SELECT COUNT(*) FROM {table_name} WHERE note_id IS NULL"
        remaining_params = []
        
        if piece_id is not None:
            remaining_query += " AND piece_id = ?"
            remaining_params.append(piece_id)
        
        cursor.execute(remaining_query, remaining_params)
        remaining = cursor.fetchone()[0]
        
        if remaining > 0:
            print(f"Warning: {remaining} records still have NULL note_id")
            
            # Show a few examples of unmatched records for debugging
            example_query = f"""
                SELECT {pk_column}, piece_id, voice, onset 
                FROM {table_name} 
                WHERE note_id IS NULL 
                {' AND piece_id = ?' if piece_id is not None else ''}
                LIMIT 3
            """
            cursor.execute(example_query, remaining_params)
            examples = cursor.fetchall()
            
            print("  Examples of unmatched records:")
            for example in examples:
                print(f"    {pk_column}={example[0]}, piece_id={example[1]}, voice={example[2]}, onset={example[3]}")
        
        # Calculate success rate
        success_rate = (direct_updated / total_count * 100) if total_count > 0 else 0
        print(f"✓ Batch update completed: {direct_updated}/{total_count} records ({success_rate:.1f}% success)")
        
        # Clean up
        cursor.execute("DROP TABLE IF EXISTS temp_note_mapping")
        
        cursor.connection.commit()
        cursor.connection.close()
        
        return direct_updated
    
    def _update_in_batches(self, cursor, table_name: str, pk_column: str,
                          piece_id: Optional[int], tolerance: float, 
                          total_count: int, batch_size: int) -> int:
        """Update records in smaller batches for better progress tracking."""
        
        print(f"Using batch processing: {batch_size} records per batch")
        
        # Get all record IDs that need updating
        where_clause = "WHERE note_id IS NULL"
        params = []
        if piece_id is not None:
            where_clause += " AND piece_id = ?"
            params.append(piece_id)
        
        cursor.execute(f"SELECT {pk_column} FROM {table_name} {where_clause} ORDER BY {pk_column}", params)
        all_ids = [row[0] for row in cursor.fetchall()]
        
        total_updated = 0
        
        # Process in batches
        for i in range(0, len(all_ids), batch_size):
            batch_ids = all_ids[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(all_ids) + batch_size - 1) // batch_size
            
            print(f"  Processing batch {batch_num}/{total_batches} ({len(batch_ids)} records)...")
            
            # Create placeholders for the IN clause
            placeholders = ','.join(['?' for _ in batch_ids])
            
            # Use simpler approach: create temporary table for this batch too
            cursor.execute("DROP TABLE IF EXISTS temp_batch_mapping")
            
            cursor.execute(f"""
                CREATE TEMP TABLE temp_batch_mapping AS
                SELECT 
                    t.{pk_column} as target_id,
                    n.note_id as matched_note_id
                FROM {table_name} t
                LEFT JOIN notes n ON (
                    n.piece_id = t.piece_id 
                    AND n.voice = t.voice 
                    AND ABS(n.onset - t.onset) <= ?
                )
                WHERE t.{pk_column} IN ({placeholders})
            """, [tolerance] + batch_ids)
            
            # Update this batch using the temporary mapping
            cursor.execute(f"""
                UPDATE {table_name}
                SET note_id = (
                    SELECT matched_note_id 
                    FROM temp_batch_mapping 
                    WHERE target_id = {table_name}.{pk_column}
                )
                WHERE {pk_column} IN (
                    SELECT target_id 
                    FROM temp_batch_mapping 
                    WHERE matched_note_id IS NOT NULL
                )
            """)
            
            batch_updated = cursor.rowcount
            total_updated += batch_updated
            
            progress = (i + len(batch_ids)) / len(all_ids) * 100
            print(f"    Batch {batch_num} completed: {batch_updated}/{len(batch_ids)} updated ({progress:.1f}% overall)")
            
            # Clean up batch table
            cursor.execute("DROP TABLE IF EXISTS temp_batch_mapping")
        
        cursor.connection.commit()
        cursor.connection.close()
        
        return total_updated

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
    parser.add_argument('--optimize', action='store_true',
                       help='Use optimized batch update method (much faster)')
    parser.add_argument('--create-indexes', action='store_true',
                       help='Create optimal indexes before updating')
    
    args = parser.parse_args()
    
    updater = NoteIdUpdater()
    
    # Create indexes if requested
    if args.create_indexes:
        updater.ensure_optimal_indexes()
    
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
    
    # Update note_ids - use optimized method if requested
    if args.optimize:
        print("Using optimized batch update method...")
        if args.table == 'all':
            results = {}
            for table in ['melodic_intervals', 'melodic_ngrams', 'melodic_entries']:
                print(f"\n--- Optimized update for {table} ---")
                results[table] = updater.update_note_ids_batch_optimized(table, args.piece_id, args.tolerance)
            
            total_updated = sum(results.values())
            print(f"\n=== Optimized Update Summary ===")
            for table, count in results.items():
                print(f"{table}: {count} records updated")
            print(f"Total: {total_updated} records updated")
        else:
            updater.update_note_ids_batch_optimized(args.table, args.piece_id, args.tolerance)
    else:
        # Use original method
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
