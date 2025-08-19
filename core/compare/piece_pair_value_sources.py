#!/usr/bin/env python3
"""
Populate piece_pair_value_sources table with shared ngram values between piece pairs
broken down by parameter sets.

This script creates a detailed mapping of shared ngram values between every 
pair of pieces, showing exactly which parameter sets contribute to each shared 
pattern. This enables analysis of how different parameter choices affect 
similarity detection.

The piece_pair_value_sources table provides granular insight into the sources
of musical similarities by tracking the specific parameter sets that generate
each shared ngram value.
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

class PiecePairValueSourcesPopulator:
    """Populate piece_pair_value_sources table with shared ngram values by sets"""
    
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
        
    def get_sets_info(self) -> Dict[int, Dict[str, Any]]:
        """Get all melodic ngram sets information"""
        query = """
        SELECT set_id, slug, description, melodic_interval_set_id, ngrams_number, ngrams_entry
        FROM melodic_ngram_sets
        ORDER BY set_id
        """
        
        cursor = self.conn.cursor()
        cursor.execute(query)
        
        sets_info = {}
        for row in cursor.fetchall():
            sets_info[row['set_id']] = {
                'slug': row['slug'],
                'description': row['description'],
                'melodic_interval_set_id': row['melodic_interval_set_id'],
                'ngrams_number': row['ngrams_number'],
                'ngrams_entry': row['ngrams_entry']
            }
        
        print(f"Found {len(sets_info)} parameter sets in database")
        return sets_info
        
    def get_piece_set_ngram_values(self) -> Dict[Tuple[int, int], Dict[str, List[int]]]:
        """
        Get ngram values for each (piece, set) combination with their corresponding note_ids.
        Returns: {(piece_id, set_id): {ngram_value: [note_ids]}}
        """
        print("Loading piece-set ngram values...")
        
        query = """
        SELECT 
            mn.piece_id,
            mn.melodic_ngram_set_id as set_id,
            mn.ngram as ngram_value,
            mn.note_id
        FROM melodic_ngrams mn
        ORDER BY mn.piece_id, mn.melodic_ngram_set_id, mn.ngram
        """
        
        cursor = self.conn.cursor()
        cursor.execute(query)
        
        piece_set_ngrams = defaultdict(lambda: defaultdict(list))
        total_rows = 0
        
        for row in cursor.fetchall():
            piece_id = row['piece_id']
            set_id = row['set_id']
            ngram_value = row['ngram_value']
            note_id = row['note_id']
            
            key = (piece_id, set_id)
            piece_set_ngrams[key][ngram_value].append(note_id)
            total_rows += 1
            
            if total_rows % 10000 == 0:
                print(f"  Processed {total_rows:,} ngram records...")
        
        print(f"  Loaded {total_rows:,} ngram records for {len(piece_set_ngrams)} (piece, set) combinations")
        
        # Convert to regular dict for cleaner handling
        result = {}
        for key, ngrams in piece_set_ngrams.items():
            result[key] = dict(ngrams)
        
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
        
    def determine_set_family_similarity(self, set_a_info: Dict, set_b_info: Dict) -> bool:
        """
        Determine if two sets belong to the same family (same base parameters except entry).
        """
        # Same family if they have same melodic_interval_set_id and ngrams_number
        # (entry parameter can be different)
        return (set_a_info['melodic_interval_set_id'] == set_b_info['melodic_interval_set_id'] and
                set_a_info['ngrams_number'] == set_b_info['ngrams_number'])
        
    def find_shared_values_by_sets(self, 
                                  piece_set_ngrams: Dict[Tuple[int, int], Dict[str, List[int]]], 
                                  piece_pairs: List[Tuple[int, int]],
                                  pieces_info: Dict[int, Dict[str, Any]],
                                  sets_info: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find shared ngram values between each piece pair across all set combinations.
        Returns list of records to insert into piece_pair_value_sources table.
        """
        print("Finding shared ngram values between piece pairs across all set combinations...")
        
        shared_records = []
        total_pairs = len(piece_pairs)
        
        # Get all set IDs
        set_ids = list(sets_info.keys())
        
        for pair_idx, (piece_a_id, piece_b_id) in enumerate(piece_pairs):
            if pair_idx % 10 == 0:
                print(f"  Processed {pair_idx:,}/{total_pairs:,} pairs ({pair_idx/total_pairs*100:.1f}%)")
            
            # Get piece metadata
            composer_a = pieces_info[piece_a_id]['composer']
            composer_b = pieces_info[piece_b_id]['composer']
            same_composer = (composer_a == composer_b)
            
            # Check all combinations of sets between the two pieces
            for set_a_id in set_ids:
                for set_b_id in set_ids:
                    # Get ngram values for both (piece, set) combinations
                    key_a = (piece_a_id, set_a_id)
                    key_b = (piece_b_id, set_b_id)
                    
                    ngrams_a = piece_set_ngrams.get(key_a, {})
                    ngrams_b = piece_set_ngrams.get(key_b, {})
                    
                    # Skip if either piece-set combination has no ngrams
                    if not ngrams_a or not ngrams_b:
                        continue
                    
                    # Find shared ngram values
                    shared_values = set(ngrams_a.keys()) & set(ngrams_b.keys())
                    
                    if not shared_values:
                        continue
                    
                    # Get set metadata
                    set_a_info = sets_info[set_a_id]
                    set_b_info = sets_info[set_b_id]
                    same_set_family = self.determine_set_family_similarity(set_a_info, set_b_info)
                    
                    # Create records for each shared value
                    for ngram_value in shared_values:
                        notes_in_a = ngrams_a[ngram_value]
                        notes_in_b = ngrams_b[ngram_value]
                        
                        # Remove duplicates and sort
                        unique_notes_a = sorted(list(set(notes_in_a)))
                        unique_notes_b = sorted(list(set(notes_in_b)))
                        
                        count_a = len(notes_in_a)
                        count_b = len(notes_in_b)
                        pairs_count = count_a * count_b
                        
                        record = {
                            'piece_a_id': piece_a_id,
                            'piece_b_id': piece_b_id,
                            'ngram_value': ngram_value,
                            'set_a_id': set_a_id,
                            'set_b_id': set_b_id,
                            'notes_in_a': json.dumps(unique_notes_a),
                            'notes_in_b': json.dumps(unique_notes_b),
                            'count_in_a': count_a,
                            'count_in_b': count_b,
                            'pairs_count': pairs_count,
                            'set_a_slug': set_a_info['slug'],
                            'set_b_slug': set_b_info['slug'],
                            'same_set_family': same_set_family,
                            'composer_a': composer_a,
                            'composer_b': composer_b,
                            'same_composer': same_composer
                        }
                        
                        shared_records.append(record)
        
        print(f"  Found {len(shared_records):,} shared value source records across all pairs and sets")
        return shared_records
        
    def insert_piece_pair_value_sources(self, shared_records: List[Dict[str, Any]]) -> int:
        """Insert shared value source records into piece_pair_value_sources table"""
        
        print("Inserting piece pair value sources into database...")
        
        # Clear existing data
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM piece_pair_value_sources")
        print("  Cleared existing data")
        
        if not shared_records:
            print("  No shared records to insert")
            return 0
        
        insert_sql = """
        INSERT INTO piece_pair_value_sources (
            piece_a_id, piece_b_id, ngram_value, set_a_id, set_b_id,
            notes_in_a, notes_in_b, count_in_a, count_in_b, pairs_count,
            set_a_slug, set_b_slug, same_set_family,
            composer_a, composer_b, same_composer
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Prepare batch data
        batch_data = []
        for record in shared_records:
            row_data = (
                record['piece_a_id'],
                record['piece_b_id'],
                record['ngram_value'],
                record['set_a_id'],
                record['set_b_id'],
                record['notes_in_a'],
                record['notes_in_b'],
                record['count_in_a'],
                record['count_in_b'],
                record['pairs_count'],
                record['set_a_slug'],
                record['set_b_slug'],
                record['same_set_family'],
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
            if batch_num % 10 == 0 or batch_num == total_batches:
                print(f"  Inserted batch {batch_num}/{total_batches} ({inserted_count:,}/{len(batch_data):,} records)")
        
        self.conn.commit()
        print(f"  Successfully inserted {inserted_count:,} piece pair value source records")
        
        return inserted_count
        
    def generate_statistics(self):
        """Generate and display statistics about the populated data"""
        
        print("\n=== Statistics ===")
        
        cursor = self.conn.cursor()
        
        # Total records
        cursor.execute("SELECT COUNT(*) FROM piece_pair_value_sources")
        total_records = cursor.fetchone()[0]
        print(f"Total piece pair value source records: {total_records:,}")
        
        # Unique piece pairs
        cursor.execute("SELECT COUNT(DISTINCT piece_a_id || '_' || piece_b_id) FROM piece_pair_value_sources")
        unique_pairs = cursor.fetchone()[0]
        print(f"Unique piece pairs with shared values: {unique_pairs:,}")
        
        # Unique set combinations
        cursor.execute("SELECT COUNT(DISTINCT set_a_id || '_' || set_b_id) FROM piece_pair_value_sources")
        unique_set_combos = cursor.fetchone()[0]
        print(f"Unique set combinations: {unique_set_combos:,}")
        
        # Unique ngram values
        cursor.execute("SELECT COUNT(DISTINCT ngram_value) FROM piece_pair_value_sources")
        unique_values = cursor.fetchone()[0]
        print(f"Unique ngram values found: {unique_values:,}")
        
        # By same set family
        cursor.execute("""
            SELECT same_set_family,
                   COUNT(*) as record_count,
                   COUNT(DISTINCT piece_a_id || '_' || piece_b_id) as unique_pairs,
                   COUNT(DISTINCT set_a_id || '_' || set_b_id) as unique_set_combos
            FROM piece_pair_value_sources
            GROUP BY same_set_family
        """)
        
        print("\nBy set family relationship:")
        for row in cursor.fetchall():
            same_family, record_count, unique_pairs, unique_set_combos = row
            family_type = "Same set family" if same_family else "Different set families"
            print(f"  {family_type}: {record_count:,} records, {unique_pairs:,} pairs, {unique_set_combos:,} set combos")
        
        # By same composer
        cursor.execute("""
            SELECT same_composer,
                   COUNT(*) as record_count,
                   COUNT(DISTINCT piece_a_id || '_' || piece_b_id) as unique_pairs
            FROM piece_pair_value_sources
            GROUP BY same_composer
        """)
        
        print("\nBy composer relationship:")
        for row in cursor.fetchall():
            same_composer, record_count, unique_pairs = row
            composer_type = "Same composer" if same_composer else "Different composers"
            print(f"  {composer_type}: {record_count:,} records, {unique_pairs:,} pairs")
        
        # Top set combinations by record count
        cursor.execute("""
            SELECT set_a_slug, set_b_slug, same_set_family,
                   COUNT(*) as record_count,
                   COUNT(DISTINCT piece_a_id || '_' || piece_b_id) as unique_pairs
            FROM piece_pair_value_sources
            GROUP BY set_a_id, set_b_id, set_a_slug, set_b_slug, same_set_family
            ORDER BY record_count DESC
            LIMIT 10
        """)
        
        print("\nMost productive set combinations:")
        for i, row in enumerate(cursor.fetchall(), 1):
            set_a_slug, set_b_slug, same_family, record_count, unique_pairs = row
            family_mark = "★" if same_family else " "
            print(f"  {i:2d}. {set_a_slug} × {set_b_slug} {family_mark}: {record_count:,} records, {unique_pairs:,} pairs")
        
        # Total potential pairings
        cursor.execute("SELECT SUM(pairs_count) FROM piece_pair_value_sources")
        total_pairs = cursor.fetchone()[0]
        print(f"\nTotal potential note pairings: {total_pairs:,}")
            
    def populate_piece_pair_value_sources(self):
        """Main method to populate piece_pair_value_sources table"""
        
        print("=== Populating Piece Pair Value Sources Table ===")
        print(f"Database: {self.db_path}")
        
        try:
            # Connect to database
            self.connect_db()
            
            # Get pieces information
            pieces_info = self.get_pieces_info()
            
            if not pieces_info:
                print("No pieces found. Please run the ingestion pipeline first.")
                return False
            
            # Get sets information
            sets_info = self.get_sets_info()
            
            if not sets_info:
                print("No parameter sets found. Please run the ingestion pipeline first.")
                return False
            
            # Get piece-set ngram values
            piece_set_ngrams = self.get_piece_set_ngram_values()
            
            if not piece_set_ngrams:
                print("No ngram data found. Please run the ngram ingestion first.")
                return False
            
            # Generate piece pairs
            piece_ids = sorted(pieces_info.keys())
            piece_pairs = self.generate_piece_pairs(piece_ids)
            
            if not piece_pairs:
                print("Not enough pieces to create pairs.")
                return False
            
            # Find shared values by sets
            shared_records = self.find_shared_values_by_sets(piece_set_ngrams, piece_pairs, pieces_info, sets_info)
            
            # Insert into database
            inserted_count = self.insert_piece_pair_value_sources(shared_records)
            
            # Generate statistics
            self.generate_statistics()
            
            print(f"\n✅ Successfully populated piece_pair_value_sources table!")
            print(f"   Analyzed {len(piece_pairs):,} piece pairs across {len(sets_info):,} parameter sets")
            print(f"   Created {inserted_count:,} shared value source records")
            
            return True
            
        except Exception as e:
            print(f"❌ Error populating piece_pair_value_sources: {e}")
            if self.conn:
                self.conn.rollback()
            return False
            
        finally:
            self.close_db()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Populate piece_pair_value_sources table')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show analysis without modifying database')
    
    args = parser.parse_args()
    
    populator = PiecePairValueSourcesPopulator()
    
    if args.dry_run:
        print("=== Dry Run Mode ===")
        # TODO: Implement dry run functionality
        print("Dry run mode not yet implemented")
        return 1
    else:
        success = populator.populate_piece_pair_value_sources()
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
