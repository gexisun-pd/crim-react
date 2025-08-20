#!/usr/bin/env python3
"""
Populate piece_pair_values table with shared ngram values between piece pairs.

This script creates a comprehensive mapping of shared ngram values between every 
pair of pieces in the database. For each piece pair, it finds all ngram values 
that appear in both pieces and stores the corresponding note_ids from each piece.

The piece_pair_values table enables efficient analysis of musical similarities
between pieces by providing quick access to shared melodic patterns.
"""

import sqlite3
import os
import sys
import json
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any
import argparse
import itertools

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from core.config import CONFIG

class PiecePairValuesPopulator:
    """Populate piece_pair_values table with shared ngram values between pieces"""
    
    def __init__(self):
        self.db_path = os.path.join(project_root, 'database', 'analysis.db')
        self.conn = None
        
    def connect_db(self):
        """Connect to the database"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        return self.conn
        
    def close_db(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            
    def get_pieces_info(self) -> Dict[int, Dict[str, Any]]:
        """Get all pieces information"""
        query = """
        SELECT piece_id, composer, title, filename
        FROM pieces
        ORDER BY piece_id
        """
        
        cursor = self.conn.cursor()
        cursor.execute(query)
        
        pieces_info = {}
        for row in cursor.fetchall():
            pieces_info[row['piece_id']] = {
                'composer': row['composer'],
                'title': row['title'],
                'filename': row['filename']
            }
        
        print(f"Found {len(pieces_info)} pieces in database")
        return pieces_info
        
    def get_piece_ngram_values(self) -> Dict[int, Dict[str, List[int]]]:
        """
        Get ngram values for each piece with their corresponding note_ids.
        Returns: {piece_id: {ngram_value: [note_ids]}}
        """
        print("Loading piece ngram values...")
        
        query = """
        SELECT 
            mn.piece_id,
            mn.ngram as ngram_value,
            mn.note_id
        FROM melodic_ngrams mn
        ORDER BY mn.piece_id, mn.ngram
        """
        
        cursor = self.conn.cursor()
        cursor.execute(query)
        
        piece_ngrams = defaultdict(lambda: defaultdict(list))
        total_rows = 0
        
        for row in cursor.fetchall():
            piece_id = row['piece_id']
            ngram_value = row['ngram_value']
            note_id = row['note_id']
            
            piece_ngrams[piece_id][ngram_value].append(note_id)
            total_rows += 1
            
            if total_rows % 10000 == 0:
                print(f"  Processed {total_rows:,} ngram records...")
        
        print(f"  Loaded {total_rows:,} ngram records for {len(piece_ngrams)} pieces")
        
        # Convert to regular dict for cleaner handling
        result = {}
        for piece_id, ngrams in piece_ngrams.items():
            result[piece_id] = dict(ngrams)
        
        return result
        
    def generate_piece_pairs(self, piece_ids: List[int]) -> List[Tuple[int, int]]:
        """
        Generate all unique piece pairs (avoiding symmetry).
        Returns pairs where piece_a_id <= piece_b_id.
        """
        piece_pairs = []
        
        for i in range(len(piece_ids)):
            for j in range(i, len(piece_ids)):  # i <= j to avoid symmetry
                piece_a_id = piece_ids[i]
                piece_b_id = piece_ids[j]
                
                # Skip self-pairs (piece with itself)
                if piece_a_id == piece_b_id:
                    continue
                    
                piece_pairs.append((piece_a_id, piece_b_id))
        
        print(f"Generated {len(piece_pairs):,} unique piece pairs")
        return piece_pairs
        
    def find_shared_values(self, piece_ngrams: Dict[int, Dict[str, List[int]]], 
                          piece_pairs: List[Tuple[int, int]], 
                          pieces_info: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find shared ngram values between each piece pair.
        Returns list of records to insert into piece_pair_values table.
        """
        print("Finding shared ngram values between piece pairs...")
        
        shared_records = []
        total_pairs = len(piece_pairs)
        
        for idx, (piece_a_id, piece_b_id) in enumerate(piece_pairs):
            if idx % 100 == 0:
                print(f"  Processed {idx:,}/{total_pairs:,} pairs ({idx/total_pairs*100:.1f}%)")
            
            # Get ngram values for both pieces
            ngrams_a = piece_ngrams.get(piece_a_id, {})
            ngrams_b = piece_ngrams.get(piece_b_id, {})
            
            # Find shared ngram values
            shared_values = set(ngrams_a.keys()) & set(ngrams_b.keys())
            
            # Get piece metadata
            composer_a = pieces_info[piece_a_id]['composer']
            composer_b = pieces_info[piece_b_id]['composer']
            same_composer = (composer_a == composer_b)
            
            # Create records for each shared value
            for ngram_value in shared_values:
                notes_in_a = ngrams_a[ngram_value]
                notes_in_b = ngrams_b[ngram_value]
                
                # Calculate ngram length from the value string
                # ngram_value looks like "('-2', '-2', '-2')"
                try:
                    # Count commas and add 1 to get length
                    ngram_length = ngram_value.count(',') + 1
                except:
                    ngram_length = 0  # fallback
                
                record = {
                    'piece_a_id': piece_a_id,
                    'piece_b_id': piece_b_id,
                    'ngram_value': ngram_value,
                    'ngram_length': ngram_length,
                    'notes_in_a': json.dumps(sorted(notes_in_a)),
                    'notes_in_b': json.dumps(sorted(notes_in_b)),
                    'count_in_a': len(notes_in_a),
                    'count_in_b': len(notes_in_b),
                    'total_shared_notes': len(notes_in_a) + len(notes_in_b),
                    'composer_a': composer_a,
                    'composer_b': composer_b,
                    'same_composer': same_composer
                }
                
                shared_records.append(record)
        
        print(f"  Found {len(shared_records):,} shared value records across all pairs")
        return shared_records
        
    def insert_piece_pair_values(self, shared_records: List[Dict[str, Any]]) -> int:
        """Insert shared value records into piece_pair_values table"""
        
        print("Inserting piece pair values into database...")
        
        # Clear existing data
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM piece_pair_values")
        print("  Cleared existing data")
        
        if not shared_records:
            print("  No shared records to insert")
            return 0
        
        insert_sql = """
        INSERT INTO piece_pair_values (
            piece_a_id, piece_b_id, ngram_value, ngram_length,
            notes_in_a, notes_in_b, count_in_a, count_in_b, total_shared_notes,
            composer_a, composer_b, same_composer
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Prepare batch data
        batch_data = []
        for record in shared_records:
            row_data = (
                record['piece_a_id'],
                record['piece_b_id'],
                record['ngram_value'],
                record['ngram_length'],
                record['notes_in_a'],
                record['notes_in_b'],
                record['count_in_a'],
                record['count_in_b'],
                record['total_shared_notes'],
                record['composer_a'],
                record['composer_b'],
                record['same_composer']
            )
            batch_data.append(row_data)
        
        # Insert in batches for better performance
        batch_size = 1000
        total_batches = (len(batch_data) + batch_size - 1) // batch_size
        
        inserted_count = 0
        for i in range(0, len(batch_data), batch_size):
            batch = batch_data[i:i + batch_size]
            cursor.executemany(insert_sql, batch)
            inserted_count += len(batch)
            
            batch_num = i // batch_size + 1
            print(f"  Inserted batch {batch_num}/{total_batches} ({inserted_count:,}/{len(batch_data):,} records)")
        
        self.conn.commit()
        print(f"  Successfully inserted {inserted_count:,} piece pair value records")
        
        return inserted_count
        
    def generate_statistics(self):
        """Generate and display statistics about the populated data"""
        
        print("\n=== Statistics ===")
        
        cursor = self.conn.cursor()
        
        # Total records
        cursor.execute("SELECT COUNT(*) FROM piece_pair_values")
        total_records = cursor.fetchone()[0]
        print(f"Total piece pair value records: {total_records:,}")
        
        # Unique piece pairs
        cursor.execute("SELECT COUNT(DISTINCT piece_a_id || '_' || piece_b_id) FROM piece_pair_values")
        unique_pairs = cursor.fetchone()[0]
        print(f"Unique piece pairs with shared values: {unique_pairs:,}")
        
        # Unique ngram values
        cursor.execute("SELECT COUNT(DISTINCT ngram_value) FROM piece_pair_values")
        unique_values = cursor.fetchone()[0]
        print(f"Unique ngram values found in pairs: {unique_values:,}")
        
        # By ngram length
        cursor.execute("""
            SELECT ngram_length, 
                   COUNT(*) as record_count,
                   COUNT(DISTINCT ngram_value) as unique_values,
                   COUNT(DISTINCT piece_a_id || '_' || piece_b_id) as unique_pairs
            FROM piece_pair_values 
            GROUP BY ngram_length 
            ORDER BY ngram_length
        """)
        
        print("\nBy ngram length:")
        for row in cursor.fetchall():
            length, record_count, unique_values, unique_pairs = row
            print(f"  Length {length}: {record_count:,} records, {unique_values:,} unique values, {unique_pairs:,} pairs")
        
        # Same vs different composer
        cursor.execute("""
            SELECT same_composer,
                   COUNT(*) as record_count,
                   COUNT(DISTINCT piece_a_id || '_' || piece_b_id) as unique_pairs
            FROM piece_pair_values
            GROUP BY same_composer
        """)
        
        print("\nBy composer relationship:")
        for row in cursor.fetchall():
            same_composer, record_count, unique_pairs = row
            composer_type = "Same composer" if same_composer else "Different composers"
            print(f"  {composer_type}: {record_count:,} records, {unique_pairs:,} pairs")
        
        # Most shared ngram values
        cursor.execute("""
            SELECT ngram_value, 
                   COUNT(*) as pair_count,
                   SUM(total_shared_notes) as total_notes
            FROM piece_pair_values 
            GROUP BY ngram_value
            ORDER BY pair_count DESC 
            LIMIT 10
        """)
        
        print("\nMost frequently shared ngram values:")
        for i, row in enumerate(cursor.fetchall(), 1):
            ngram_value, pair_count, total_notes = row
            print(f"  {i:2d}. '{ngram_value}': shared by {pair_count:,} pairs, {total_notes:,} total notes")
        
        # Piece pairs with most shared values
        cursor.execute("""
            SELECT 
                ppv.piece_a_id, ppv.piece_b_id,
                pa.composer as composer_a, pa.title as title_a,
                pb.composer as composer_b, pb.title as title_b,
                COUNT(*) as shared_value_count,
                SUM(ppv.total_shared_notes) as total_shared_notes
            FROM piece_pair_values ppv
            JOIN pieces pa ON ppv.piece_a_id = pa.piece_id
            JOIN pieces pb ON ppv.piece_b_id = pb.piece_id
            GROUP BY ppv.piece_a_id, ppv.piece_b_id, pa.composer, pa.title, pb.composer, pb.title
            ORDER BY shared_value_count DESC
            LIMIT 10
        """)
        
        print("\nPiece pairs with most shared values:")
        for i, row in enumerate(cursor.fetchall(), 1):
            piece_a_id, piece_b_id, composer_a, title_a, composer_b, title_b, shared_count, total_notes = row
            print(f"  {i:2d}. Pieces {piece_a_id}-{piece_b_id}: {shared_count:,} shared values, {total_notes:,} notes")
            print(f"      A: {composer_a} - {title_a}")
            print(f"      B: {composer_b} - {title_b}")
            
    def populate_piece_pair_values(self):
        """Main method to populate piece_pair_values table"""
        
        print("=== Populating Piece Pair Values Table ===")
        print(f"Database: {self.db_path}")
        
        try:
            # Connect to database
            self.connect_db()
            
            # Get pieces information
            pieces_info = self.get_pieces_info()
            
            if not pieces_info:
                print("No pieces found. Please run the ingestion pipeline first.")
                return False
            
            # Get piece ngram values
            piece_ngrams = self.get_piece_ngram_values()
            
            if not piece_ngrams:
                print("No ngram data found. Please run the ngram ingestion first.")
                return False
            
            # Generate piece pairs
            piece_ids = sorted(pieces_info.keys())
            piece_pairs = self.generate_piece_pairs(piece_ids)
            
            if not piece_pairs:
                print("Not enough pieces to create pairs.")
                return False
            
            # Find shared values
            shared_records = self.find_shared_values(piece_ngrams, piece_pairs, pieces_info)
            
            # Insert into database
            inserted_count = self.insert_piece_pair_values(shared_records)
            
            # Generate statistics
            self.generate_statistics()
            
            print(f"\n✅ Successfully populated piece_pair_values table!")
            print(f"   Analyzed {len(piece_pairs):,} piece pairs")
            print(f"   Created {inserted_count:,} shared value records")
            
            return True
            
        except Exception as e:
            print(f"❌ Error populating piece_pair_values: {e}")
            if self.conn:
                self.conn.rollback()
            return False
            
        finally:
            self.close_db()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Populate piece_pair_values table')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show analysis without modifying database')
    
    args = parser.parse_args()
    
    populator = PiecePairValuesPopulator()
    
    if args.dry_run:
        print("=== Dry Run Mode ===")
        # TODO: Implement dry run functionality
        print("Dry run mode not yet implemented")
        return 1
    else:
        success = populator.populate_piece_pair_values()
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())