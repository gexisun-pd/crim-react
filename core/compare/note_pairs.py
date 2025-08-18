#!/usr/bin/env python3
"""
Generate note_pairs table data.

This script creates all possible pairs of notes from the notes table,
with metadata for comparison analysis including composer, piece, voice, and timing information.
"""

import sqlite3
import os
import sys
import time
from typing import Optional, Tuple

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

class NotePairsGenerator:
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the note pairs generator"""
        if db_path is None:
            self.db_path = os.path.join(project_root, 'database', 'analysis.db')
        else:
            self.db_path = db_path
    
    def check_prerequisites(self) -> bool:
        """Check if database and required tables exist"""
        if not os.path.exists(self.db_path):
            print(f"Database not found at: {self.db_path}")
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if notes table exists and has data
            cursor.execute("SELECT COUNT(*) FROM notes")
            notes_count = cursor.fetchone()[0]
            
            if notes_count == 0:
                print("No notes found in database. Please run ingestion first.")
                return False
            
            # Check if note_pairs table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='note_pairs'
            """)
            
            if not cursor.fetchone():
                print("note_pairs table not found. Please run init_compare_db.py first.")
                return False
            
            print(f"Found {notes_count:,} notes in database")
            return True
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()
    
    def get_table_statistics(self) -> dict:
        """Get statistics about the database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # Notes statistics
            cursor.execute("SELECT COUNT(*) FROM notes")
            stats['total_notes'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT piece_id) FROM notes")
            stats['total_pieces'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT voice) FROM notes")
            stats['total_voices'] = cursor.fetchone()[0]
            
            # Get composer information from pieces table
            cursor.execute("""
                SELECT COUNT(DISTINCT p.composer) 
                FROM pieces p
                INNER JOIN notes n ON p.piece_id = n.piece_id
            """)
            stats['total_composers'] = cursor.fetchone()[0]
            
            # Existing note_pairs
            cursor.execute("SELECT COUNT(*) FROM note_pairs")
            stats['existing_pairs'] = cursor.fetchone()[0]
            
            # Estimated total pairs (n choose 2 + n for self-pairs)
            n = stats['total_notes']
            stats['estimated_total_pairs'] = (n * (n + 1)) // 2
            
            return stats
            
        except sqlite3.Error as e:
            print(f"Error getting statistics: {e}")
            return {}
        finally:
            conn.close()
    
    def clear_existing_pairs(self) -> bool:
        """Clear existing note pairs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM note_pairs")
            deleted_count = cursor.rowcount
            conn.commit()
            print(f"Cleared {deleted_count:,} existing note pairs")
            return True
            
        except sqlite3.Error as e:
            print(f"Error clearing existing pairs: {e}")
            return False
        finally:
            conn.close()
    
    def generate_note_pairs(self, batch_size: int = 10000, clear_existing: bool = False) -> bool:
        """
        Generate all note pairs with metadata.
        
        Args:
            batch_size: Number of pairs to process in each batch
            clear_existing: Whether to clear existing pairs first
        """
        
        if not self.check_prerequisites():
            return False
        
        # Get statistics
        stats = self.get_table_statistics()
        print(f"Database Statistics:")
        print(f"  Total notes: {stats['total_notes']:,}")
        print(f"  Total pieces: {stats['total_pieces']:,}")
        print(f"  Total composers: {stats['total_composers']:,}")
        print(f"  Estimated pairs: {stats['estimated_total_pairs']:,}")
        print(f"  Existing pairs: {stats['existing_pairs']:,}")
        
        # Handle existing pairs
        if stats['existing_pairs'] > 0:
            if clear_existing:
                if not self.clear_existing_pairs():
                    return False
            else:
                response = input("Note pairs already exist. Clear and regenerate? (y/N): ")
                if response.lower() != 'y':
                    print("Keeping existing pairs. Exiting.")
                    return True
                if not self.clear_existing_pairs():
                    return False
        
        # Start generation
        print(f"\nGenerating note pairs in batches of {batch_size:,}...")
        start_time = time.time()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enable WAL mode for better performance
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=10000")
        
        try:
            # Use a single SQL query to generate all pairs efficiently
            insert_sql = """
            INSERT INTO note_pairs (
                note_a_id, note_b_id, 
                composer_a, composer_b, same_composer,
                piece_a_id, piece_b_id, same_piece,
                voice_a, voice_b, same_voice,
                onset_a, onset_b
            )
            SELECT 
                a.note_id as note_a_id,
                b.note_id as note_b_id,
                pa.composer as composer_a,
                pb.composer as composer_b,
                (pa.composer = pb.composer) as same_composer,
                a.piece_id as piece_a_id,
                b.piece_id as piece_b_id,
                (a.piece_id = b.piece_id) as same_piece,
                a.voice as voice_a,
                b.voice as voice_b,
                (a.voice = b.voice) as same_voice,
                a.onset as onset_a,
                b.onset as onset_b
            FROM notes a
            CROSS JOIN notes b
            INNER JOIN pieces pa ON a.piece_id = pa.piece_id
            INNER JOIN pieces pb ON b.piece_id = pb.piece_id
            WHERE a.note_id <= b.note_id
            """
            
            print("Executing note pairs generation query...")
            cursor.execute(insert_sql)
            pairs_created = cursor.rowcount
            
            conn.commit()
            
            elapsed_time = time.time() - start_time
            print(f"\n✓ Successfully created {pairs_created:,} note pairs")
            print(f"⏱ Total time: {elapsed_time:.1f} seconds")
            print(f"📊 Rate: {pairs_created/elapsed_time:.0f} pairs/second")
            
            # Get final statistics
            self._print_generation_statistics(cursor)
            
            return True
            
        except sqlite3.Error as e:
            print(f"Error generating note pairs: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _print_generation_statistics(self, cursor):
        """Print statistics about the generated pairs"""
        print(f"\n=== Note Pairs Statistics ===")
        
        # Total pairs
        cursor.execute("SELECT COUNT(*) FROM note_pairs")
        total_pairs = cursor.fetchone()[0]
        print(f"Total pairs: {total_pairs:,}")
        
        # Self pairs (same note)
        cursor.execute("SELECT COUNT(*) FROM note_pairs WHERE note_a_id = note_b_id")
        self_pairs = cursor.fetchone()[0]
        print(f"Self pairs: {self_pairs:,}")
        
        # Same piece pairs
        cursor.execute("SELECT COUNT(*) FROM note_pairs WHERE same_piece = 1")
        same_piece = cursor.fetchone()[0]
        print(f"Same piece pairs: {same_piece:,} ({same_piece/total_pairs*100:.1f}%)")
        
        # Cross piece pairs
        cross_piece = total_pairs - same_piece
        print(f"Cross piece pairs: {cross_piece:,} ({cross_piece/total_pairs*100:.1f}%)")
        
        # Same composer pairs
        cursor.execute("SELECT COUNT(*) FROM note_pairs WHERE same_composer = 1")
        same_composer = cursor.fetchone()[0]
        print(f"Same composer pairs: {same_composer:,} ({same_composer/total_pairs*100:.1f}%)")
        
        # Cross composer pairs
        cross_composer = total_pairs - same_composer
        print(f"Cross composer pairs: {cross_composer:,} ({cross_composer/total_pairs*100:.1f}%)")
        
        # Same voice pairs
        cursor.execute("SELECT COUNT(*) FROM note_pairs WHERE same_voice = 1")
        same_voice = cursor.fetchone()[0]
        print(f"Same voice pairs: {same_voice:,} ({same_voice/total_pairs*100:.1f}%)")
        
        # Composer breakdown
        print(f"\n=== Composer Breakdown ===")
        cursor.execute("""
            SELECT 
                composer_a,
                composer_b,
                COUNT(*) as pair_count
            FROM note_pairs 
            GROUP BY composer_a, composer_b
            ORDER BY pair_count DESC
            LIMIT 10
        """)
        
        composer_pairs = cursor.fetchall()
        for composer_a, composer_b, count in composer_pairs:
            if composer_a == composer_b:
                print(f"  {composer_a} (internal): {count:,}")
            else:
                print(f"  {composer_a} ↔ {composer_b}: {count:,}")
    
    def verify_pairs_integrity(self) -> bool:
        """Verify the integrity of generated pairs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            print("\n=== Verifying Pairs Integrity ===")
            
            # Check for proper ordering (note_a_id <= note_b_id)
            cursor.execute("SELECT COUNT(*) FROM note_pairs WHERE note_a_id > note_b_id")
            bad_ordering = cursor.fetchone()[0]
            
            if bad_ordering > 0:
                print(f"❌ Found {bad_ordering} pairs with improper ordering")
                return False
            else:
                print("✓ All pairs have proper ordering (note_a_id <= note_b_id)")
            
            # Check for orphaned references
            cursor.execute("""
                SELECT COUNT(*) FROM note_pairs np
                LEFT JOIN notes na ON np.note_a_id = na.note_id
                WHERE na.note_id IS NULL
            """)
            orphaned_a = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM note_pairs np
                LEFT JOIN notes nb ON np.note_b_id = nb.note_id
                WHERE nb.note_id IS NULL
            """)
            orphaned_b = cursor.fetchone()[0]
            
            if orphaned_a > 0 or orphaned_b > 0:
                print(f"❌ Found orphaned references: {orphaned_a} in note_a, {orphaned_b} in note_b")
                return False
            else:
                print("✓ All note references are valid")
            
            # Check metadata consistency
            cursor.execute("""
                SELECT COUNT(*) FROM note_pairs np
                INNER JOIN notes na ON np.note_a_id = na.note_id
                INNER JOIN notes nb ON np.note_b_id = nb.note_id
                WHERE np.same_piece != (na.piece_id = nb.piece_id)
            """)
            bad_same_piece = cursor.fetchone()[0]
            
            if bad_same_piece > 0:
                print(f"❌ Found {bad_same_piece} pairs with incorrect same_piece flag")
                return False
            else:
                print("✓ Same piece flags are consistent")
            
            # Check voice consistency
            cursor.execute("""
                SELECT COUNT(*) FROM note_pairs np
                INNER JOIN notes na ON np.note_a_id = na.note_id
                INNER JOIN notes nb ON np.note_b_id = nb.note_id
                WHERE np.same_voice != (na.voice = nb.voice)
            """)
            bad_same_voice = cursor.fetchone()[0]
            
            if bad_same_voice > 0:
                print(f"❌ Found {bad_same_voice} pairs with incorrect same_voice flag")
                return False
            else:
                print("✓ Same voice flags are consistent")
            
            print("✅ All integrity checks passed!")
            return True
            
        except sqlite3.Error as e:
            print(f"Error during integrity check: {e}")
            return False
        finally:
            conn.close()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate note pairs for comparison analysis')
    parser.add_argument('--batch-size', type=int, default=10000,
                       help='Batch size for processing (default: 10000)')
    parser.add_argument('--clear', action='store_true',
                       help='Clear existing pairs without prompting')
    parser.add_argument('--verify', action='store_true',
                       help='Verify integrity of existing pairs')
    parser.add_argument('--stats-only', action='store_true',
                       help='Show statistics only, do not generate pairs')
    
    args = parser.parse_args()
    
    print("=== Note Pairs Generator ===")
    
    generator = NotePairsGenerator()
    
    if args.stats_only:
        stats = generator.get_table_statistics()
        print(f"Database Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value:,}")
        return
    
    if args.verify:
        generator.verify_pairs_integrity()
        return
    
    # Generate pairs
    success = generator.generate_note_pairs(
        batch_size=args.batch_size,
        clear_existing=args.clear
    )
    
    if success:
        print("\n=== Verifying Generated Pairs ===")
        generator.verify_pairs_integrity()
        
        print(f"\n✅ Note pairs generation completed successfully!")
        print(f"Next steps:")
        print(f"  - Run comparison algorithms on the generated pairs")
        print(f"  - Analyze patterns and similarities")
        print(f"  - Generate comparison reports")
    else:
        print(f"\n❌ Note pairs generation failed!")

if __name__ == "__main__":
    main()
