#!/usr/bin/env python3
"""
Script to update note_id fields in analysis tables.

This script can be run standalone to update note_id references
in melodic_intervals, melodic_ngrams, and melodic_entries tables.
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
        description='Update note_id fields in analysis tables',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update all tables for all pieces
  python scripts/update_note_ids.py
  
  # Update only melodic_entries table
  python scripts/update_note_ids.py --table melodic_entries
  
  # Update only for a specific piece
  python scripts/update_note_ids.py --piece-id 1
  
  # Add missing note_id columns first, then update
  python scripts/update_note_ids.py --add-columns
  
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
    parser.add_argument('--add-columns', action='store_true',
                       help='Add note_id columns to existing tables if missing')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be updated without making changes')
    
    args = parser.parse_args()
    
    print("=== Note ID Updater ===")
    print(f"Table(s): {args.table}")
    if args.piece_id:
        print(f"Piece ID: {args.piece_id}")
    print(f"Tolerance: {args.tolerance}")
    print(f"Dry run: {args.dry_run}")
    print()
    
    try:
        updater = NoteIdUpdater()
        
        # Add columns if requested
        if args.add_columns:
            print("Adding missing note_id columns...")
            updater.add_note_id_columns_to_existing_tables()
            print()
        
        if args.dry_run:
            print("DRY RUN MODE - No actual updates will be performed")
            print("This feature is not implemented yet")
            return
        
        # Update note_ids
        if args.table == 'all':
            results = updater.update_all_note_ids(args.piece_id, args.tolerance)
        elif args.table == 'melodic_intervals':
            count = updater.update_melodic_intervals_note_ids(args.piece_id, args.tolerance)
            results = {'melodic_intervals': count}
        elif args.table == 'melodic_ngrams':
            count = updater.update_melodic_ngrams_note_ids(args.piece_id, args.tolerance)
            results = {'melodic_ngrams': count}
        elif args.table == 'melodic_entries':
            count = updater.update_melodic_entries_note_ids(args.piece_id, args.tolerance)
            results = {'melodic_entries': count}
        
        print(f"\n=== Final Results ===")
        total_updated = sum(results.values()) if isinstance(results, dict) else results
        if isinstance(results, dict):
            for table, count in results.items():
                print(f"{table}: {count} records updated")
            print(f"Total: {total_updated} records updated")
        else:
            print(f"Total: {total_updated} records updated")
            
        if total_updated > 0:
            print("\nSuccess! Note ID references have been updated.")
        else:
            print("\nNo records needed updating.")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
