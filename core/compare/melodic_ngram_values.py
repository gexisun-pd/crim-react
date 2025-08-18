#!/usr/bin/env python3
"""
Populate melodic_ngram_values table from melodic_ngrams data.

This script creates an inverted index of melodic n-grams, organizing 
note_ids by their ngram values. For each unique ngram pattern, it 
collects all note_ids that have that pattern and stores statistics.

The melodic_ngram_values table serves as a "bucket" system where:
- Each unique ngram value maps to a list of note_ids
- Additional metadata includes piece/composer/voice statistics
- This enables efficient searching for notes with specific ngram patterns
"""

import sqlite3
import os
import sys
import json
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple
import argparse

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from core.config import CONFIG

class MelodicNgramValuesPopulator:
    """Populate melodic_ngram_values table from melodic_ngrams data"""
    
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
            
    def get_melodic_ngram_data(self) -> List[sqlite3.Row]:
        """Retrieve all melodic ngram data with associated metadata"""
        query = """
        SELECT 
            mn.ngram_id,
            mn.piece_id,
            mn.melodic_ngram_set_id,
            mn.note_id,
            mn.voice,
            mn.voice_name,
            mn.onset,
            mn.ngram,
            mn.ngram_length,
            p.composer,
            p.title as piece_title,
            p.filename
        FROM melodic_ngrams mn
        JOIN pieces p ON mn.piece_id = p.piece_id
        ORDER BY mn.melodic_ngram_set_id, mn.ngram, mn.piece_id, mn.voice, mn.onset
        """
        
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()
        
    def process_ngram_data(self, ngram_data: List[sqlite3.Row]) -> Tuple[Dict, Dict]:
        """Process ngram data and organize by ngram values"""
        
        print("Processing ngram data...")
        
        # Global aggregation by ngram value (across all sets)
        global_values = defaultdict(lambda: {
            'note_ids': [],
            'piece_ids': set(),
            'composers': set(),
            'voice_numbers': set(),
            'voice_names': set(),
            'ngram_length': None,
            'sets': set()
        })
        
        # Per-set breakdown by (ngram_value, set_id)
        set_values = defaultdict(lambda: {
            'note_ids': [],
            'piece_ids': set(),
            'composers': set(),
            'voice_numbers': set(),
            'voice_names': set(),
            'ngram_length': None,
            'melodic_ngram_set_id': None
        })
        
        total_rows = len(ngram_data)
        processed = 0
        
        for row in ngram_data:
            processed += 1
            if processed % 1000 == 0:
                print(f"  Processed {processed:,}/{total_rows:,} rows ({processed/total_rows*100:.1f}%)")
                
            ngram_value = row['ngram']
            set_id = row['melodic_ngram_set_id']
            set_key = (ngram_value, set_id)
            
            # Update global aggregation
            global_group = global_values[ngram_value]
            global_group['note_ids'].append(row['note_id'])
            global_group['piece_ids'].add(row['piece_id'])
            global_group['composers'].add(row['composer'])
            global_group['voice_numbers'].add(row['voice'])
            global_group['sets'].add(set_id)
            if row['voice_name']:
                global_group['voice_names'].add(row['voice_name'])
            if global_group['ngram_length'] is None:
                global_group['ngram_length'] = row['ngram_length']
            
            # Update per-set breakdown
            set_group = set_values[set_key]
            set_group['note_ids'].append(row['note_id'])
            set_group['piece_ids'].add(row['piece_id'])
            set_group['composers'].add(row['composer'])
            set_group['voice_numbers'].add(row['voice'])
            if row['voice_name']:
                set_group['voice_names'].add(row['voice_name'])
            if set_group['ngram_length'] is None:
                set_group['ngram_length'] = row['ngram_length']
                set_group['melodic_ngram_set_id'] = row['melodic_ngram_set_id']
        
        print(f"  Finished processing {total_rows:,} rows")
        print(f"  Found {len(global_values):,} unique ngram patterns globally")
        print(f"  Found {len(set_values):,} unique ngram-set combinations")
        
        return global_values, set_values
        
    def insert_ngram_values(self, global_values: Dict, set_values: Dict) -> Tuple[int, int]:
        """Insert processed ngram values into both tables"""
        
        print("Inserting ngram values into database...")
        
        # Clear existing data
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM melodic_ngram_value_sets")  # Delete child records first
        cursor.execute("DELETE FROM melodic_ngram_values")
        print("  Cleared existing data")
        
        # Insert global values first
        print("  Inserting global ngram values...")
        global_insert_sql = """
        INSERT INTO melodic_ngram_values (
            ngram_value,
            ngram_length,
            total_occurrences,
            total_sets,
            note_ids,
            piece_ids,
            composers,
            piece_count,
            composer_count,
            voice_numbers,
            voice_names,
            voice_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        global_batch_data = []
        value_id_map = {}  # Map ngram_value to value_id for foreign key reference
        
        for ngram_value, global_data in global_values.items():
            # Convert sets to sorted lists for JSON serialization
            note_ids = sorted(global_data['note_ids'])
            piece_ids = sorted(list(global_data['piece_ids']))
            composers = sorted(list(global_data['composers']))
            voice_numbers = sorted(list(global_data['voice_numbers']))
            voice_names = sorted(list(global_data['voice_names']))
            
            row_data = (
                ngram_value,
                global_data['ngram_length'],
                len(note_ids),                     # total_occurrences
                len(global_data['sets']),          # total_sets
                json.dumps(note_ids),              # note_ids as JSON
                json.dumps(piece_ids),             # piece_ids as JSON
                json.dumps(composers),             # composers as JSON
                len(piece_ids),                    # piece_count
                len(composers),                    # composer_count
                json.dumps(voice_numbers),         # voice_numbers as JSON
                json.dumps(voice_names),           # voice_names as JSON
                len(voice_numbers)                 # voice_count
            )
            
            global_batch_data.append(row_data)
        
        cursor.executemany(global_insert_sql, global_batch_data)
        
        # Get the auto-generated value_ids to create the mapping
        cursor.execute("SELECT value_id, ngram_value FROM melodic_ngram_values")
        for value_id, ngram_value in cursor.fetchall():
            value_id_map[ngram_value] = value_id
        
        global_count = len(global_batch_data)
        print(f"    Inserted {global_count:,} global ngram values")
        
        # Insert set-specific values
        print("  Inserting set-specific ngram values...")
        set_insert_sql = """
        INSERT INTO melodic_ngram_value_sets (
            value_id,
            melodic_ngram_set_id,
            set_occurrences,
            set_note_ids,
            set_piece_ids,
            set_composers,
            set_piece_count,
            set_composer_count,
            set_voice_numbers,
            set_voice_names,
            set_voice_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        set_batch_data = []
        
        for (ngram_value, set_id), set_data in set_values.items():
            value_id = value_id_map[ngram_value]
            
            # Convert sets to sorted lists for JSON serialization
            note_ids = sorted(set_data['note_ids'])
            piece_ids = sorted(list(set_data['piece_ids']))
            composers = sorted(list(set_data['composers']))
            voice_numbers = sorted(list(set_data['voice_numbers']))
            voice_names = sorted(list(set_data['voice_names']))
            
            row_data = (
                value_id,
                set_data['melodic_ngram_set_id'],
                len(note_ids),                     # set_occurrences
                json.dumps(note_ids),              # set_note_ids as JSON
                json.dumps(piece_ids),             # set_piece_ids as JSON
                json.dumps(composers),             # set_composers as JSON
                len(piece_ids),                    # set_piece_count
                len(composers),                    # set_composer_count
                json.dumps(voice_numbers),         # set_voice_numbers as JSON
                json.dumps(voice_names),           # set_voice_names as JSON
                len(voice_numbers)                 # set_voice_count
            )
            
            set_batch_data.append(row_data)
        
        cursor.executemany(set_insert_sql, set_batch_data)
        
        self.conn.commit()
        
        set_count = len(set_batch_data)
        print(f"    Inserted {set_count:,} set-specific ngram values")
        print(f"  Successfully inserted all data")
        
        return global_count, set_count
        
    def generate_statistics(self):
        """Generate and display statistics about the populated data"""
        
        print("\n=== Statistics ===")
        
        cursor = self.conn.cursor()
        
        # Global statistics
        cursor.execute("SELECT COUNT(*) FROM melodic_ngram_values")
        total_global_values = cursor.fetchone()[0]
        print(f"Total unique ngram values (global): {total_global_values:,}")
        
        cursor.execute("SELECT COUNT(*) FROM melodic_ngram_value_sets")
        total_set_combinations = cursor.fetchone()[0]
        print(f"Total ngram-set combinations: {total_set_combinations:,}")
        
        # Total occurrences across all sets
        cursor.execute("SELECT SUM(total_occurrences) FROM melodic_ngram_values")
        total_occurrences = cursor.fetchone()[0]
        print(f"Total ngram occurrences: {total_occurrences:,}")
        
        # Cross-set analysis
        cursor.execute("""
            SELECT total_sets, COUNT(*) as value_count
            FROM melodic_ngram_values 
            GROUP BY total_sets 
            ORDER BY total_sets DESC
        """)
        
        print("\nNgram values by number of sets they appear in:")
        for row in cursor.fetchall():
            sets_count, value_count = row
            percentage = value_count / total_global_values * 100 if total_global_values > 0 else 0
            print(f"  {sets_count} sets: {value_count:,} values ({percentage:.1f}%)")
        
        # By ngram length
        cursor.execute("""
            SELECT ngram_length, COUNT(*) as unique_count, SUM(total_occurrences) as total_count
            FROM melodic_ngram_values 
            GROUP BY ngram_length 
            ORDER BY ngram_length
        """)
        
        print("\nBy ngram length:")
        for row in cursor.fetchall():
            length, unique_count, total_count = row
            print(f"  Length {length}: {unique_count:,} unique patterns, {total_count:,} total occurrences")
        
        # Most common ngram values globally
        cursor.execute("""
            SELECT ngram_value, total_occurrences, total_sets, piece_count, composer_count
            FROM melodic_ngram_values 
            ORDER BY total_occurrences DESC 
            LIMIT 10
        """)
        
        print("\nMost common ngram patterns (global):")
        for i, row in enumerate(cursor.fetchall(), 1):
            ngram_value, total_occ, total_sets, piece_count, composer_count = row
            print(f"  {i:2d}. '{ngram_value}': {total_occ:,} occurrences, "
                  f"{total_sets} sets, {piece_count} pieces, {composer_count} composers")
        
        # Cross-set patterns (appearing in multiple sets)
        cursor.execute("""
            SELECT ngram_value, total_sets, total_occurrences, piece_count, composer_count
            FROM melodic_ngram_values 
            WHERE total_sets > 1
            ORDER BY total_sets DESC, total_occurrences DESC
            LIMIT 10
        """)
        
        print("\nCross-set patterns (appearing in multiple sets):")
        cross_set_rows = cursor.fetchall()
        if cross_set_rows:
            for i, row in enumerate(cross_set_rows, 1):
                ngram_value, total_sets, total_occ, piece_count, composer_count = row
                print(f"  {i:2d}. '{ngram_value}': {total_sets} sets, "
                      f"{total_occ:,} occurrences, {piece_count} pieces, {composer_count} composers")
        else:
            print("  No patterns found in multiple sets")
            
        # Example of detailed breakdown for a cross-set pattern
        if cross_set_rows:
            example_ngram = cross_set_rows[0][0]
            cursor.execute("""
                SELECT 
                    mvs.melodic_ngram_set_id,
                    mns.slug,
                    mvs.set_occurrences,
                    mvs.set_piece_count,
                    mvs.set_composer_count
                FROM melodic_ngram_value_sets mvs
                JOIN melodic_ngram_values mv ON mvs.value_id = mv.value_id
                JOIN melodic_ngram_sets mns ON mvs.melodic_ngram_set_id = mns.set_id
                WHERE mv.ngram_value = ?
                ORDER BY mvs.set_occurrences DESC
            """, (example_ngram,))
            
            print(f"\nDetailed breakdown for '{example_ngram}':")
            for row in cursor.fetchall():
                set_id, slug, set_occ, set_pieces, set_composers = row
                print(f"  Set {set_id} ({slug}): {set_occ:,} occurrences, "
                      f"{set_pieces} pieces, {set_composers} composers")
            
    def populate_melodic_ngram_values(self):
        """Main method to populate melodic_ngram_values table"""
        
        print("=== Populating Melodic Ngram Values Table ===")
        print(f"Database: {self.db_path}")
        
        try:
            # Connect to database
            self.connect_db()
            
            # Get ngram data
            print("Retrieving melodic ngram data...")
            ngram_data = self.get_melodic_ngram_data()
            
            if not ngram_data:
                print("No melodic ngram data found. Please run the ngram ingestion first.")
                return False
            
            print(f"Found {len(ngram_data):,} melodic ngram records")
            
            # Process data
            global_values, set_values = self.process_ngram_data(ngram_data)
            
            # Insert into database
            global_count, set_count = self.insert_ngram_values(global_values, set_values)
            
            # Generate statistics
            self.generate_statistics()
            
            print(f"\n✅ Successfully populated melodic_ngram_values tables!")
            print(f"   Processed {len(ngram_data):,} ngram records")
            print(f"   Created {global_count:,} global ngram value entries")
            print(f"   Created {set_count:,} set-specific ngram value entries")
            
            return True
            
        except Exception as e:
            print(f"❌ Error populating melodic_ngram_values: {e}")
            if self.conn:
                self.conn.rollback()
            return False
            
        finally:
            self.close_db()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Populate melodic_ngram_values table')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show statistics without modifying database')
    
    args = parser.parse_args()
    
    populator = MelodicNgramValuesPopulator()
    
    if args.dry_run:
        print("=== Dry Run Mode ===")
        # TODO: Implement dry run functionality
        print("Dry run mode not yet implemented")
        return 1
    else:
        success = populator.populate_melodic_ngram_values()
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
