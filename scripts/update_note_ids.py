#!/usr/bin/env python3
"""
Script to update note_id fields in analysis tables using optimized batch processing.

This script finds and updates note_id references in melodic_intervals, melodic_ngrams, 
and melodic_entries tables by matching piece_id, voice, and onset with the notes table.
Uses optimized batch processing for fast performance on large datasets.
"""

import os
import sys
import argparse

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(project_root)

from core.utils.note_id_updater import NoteIdUpdater


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Update note_id fields in analysis tables using batch processing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update all tables for all pieces
  python scripts/update_note_ids.py
  
  # Update only melodic_entries table
  python scripts/update_note_ids.py --table melodic_entries
  
  # Update only for a specific piece
  python scripts/update_note_ids.py --piece-id 1
  
  # Use custom batch size for very large datasets
  python scripts/update_note_ids.py --batch-size 10000
  
  # Use custom tolerance for onset matching
  python scripts/update_note_ids.py --tolerance 0.01
        """
    )
    
    parser.add_argument('--piece-id', type=int, 
                       help='Update only records for specific piece_id')
    parser.add_argument('--tolerance', type=float, default=0.001, 
                       help='Tolerance for onset matching (default: 0.001)')
    parser.add_argument('--table', 
                       choices=['melodic_intervals', 'melodic_ngrams', 'melodic_entries', 'all'],
                       default='all', 
                       help='Which table(s) to update (default: all)')
    parser.add_argument('--batch-size', type=int, default=5000,
                       help='Batch size for processing large datasets (default: 5000)')
    
    args = parser.parse_args()
    
    print("=== Note ID Updater (Batch Processing) ===")
    print(f"Table(s): {args.table}")
    if args.piece_id:
        print(f"Piece ID: {args.piece_id}")
    print(f"Tolerance: {args.tolerance}")
    print(f"Batch Size: {args.batch_size}")
    print()
    
    try:
        updater = NoteIdUpdater()
        
        # Update note_ids using optimized batch processing
        if args.table == 'all':
            results = {}
            for table_name in ['melodic_intervals', 'melodic_ngrams', 'melodic_entries']:
                count = updater.update_note_ids_batch_optimized(table_name, args.piece_id, args.tolerance, args.batch_size)
                results[table_name] = count
        elif args.table in ['melodic_intervals', 'melodic_ngrams', 'melodic_entries']:
            count = updater.update_note_ids_batch_optimized(args.table, args.piece_id, args.tolerance, args.batch_size)
            results = {args.table: count}
        
        print(f"\n=== Final Results ===")
        total_updated = sum(results.values()) if isinstance(results, dict) else results
        if isinstance(results, dict):
            for table, count in results.items():
                print(f"{table}: {count} records updated")
            print(f"Total: {total_updated} records updated")
        else:
            print(f"Total: {total_updated} records updated")
            
        if total_updated > 0:
            print("\nSuccess! Note ID references have been updated using batch processing.")
        else:
            print("\nNo records needed updating.")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
