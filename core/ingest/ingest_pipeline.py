#!/usr/bin/env python3
"""
Complete Music Analysis Ingestion Pipeline

This script runs all ingestion steps in the correct order:
1. Initialize database and parameter sets
2. Ingest pieces (MusicXML files)
3. Ingest notes from pieces
4. Ingest melodic intervals
5. Ingest melodic n-grams
6. Ingest melodic entries

Usage:
    python core/ingest/run_full_pipeline.py                    # Full pipeline
    python core/ingest/run_full_pipeline.py --skip-init        # Skip database initialization
    python core/ingest/run_full_pipeline.py --step notes       # Run only specific step
    python core/ingest/run_full_pipeline.py --from intervals   # Start from specific step
"""

import os
import sys
import subprocess
import time
import argparse
from typing import List, Optional

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

class IngestionPipeline:
    """Complete ingestion pipeline manager"""
    
    def __init__(self):
        self.project_root = project_root
        self.steps = [
            ('init', 'Initialize Database', 'core/db/init_db.py'),
            ('pieces', 'Ingest Pieces', 'core/ingest/ingest_pieces.py'),
            ('notes', 'Ingest Notes', 'core/ingest/ingest_notes.py'),
            ('note_entry', 'Ingest Note Entry', 'core/ingest/ingest_note_entry.py'),
            ('intervals', 'Ingest Melodic Intervals', 'core/ingest/ingest_melodic_intervals.py'),
            ('ngrams', 'Ingest Melodic N-grams', 'core/ingest/ingest_melodic_ngrams.py')
        ]
        
        self.step_map = {step[0]: step for step in self.steps}
    
    def print_banner(self, title: str):
        """Print a formatted banner"""
        print("\n" + "=" * 80)
        print(f"=== {title} ===")
        print("=" * 80)
    
    def print_step_header(self, step_num: int, total_steps: int, step_name: str, description: str):
        """Print step header"""
        print(f"\n{'#' * 60}")
        print(f"# Step {step_num}/{total_steps}: {description}")
        print(f"# Script: {step_name}")
        print(f"{'#' * 60}")
    
    def run_script(self, script_path: str, step_name: str) -> bool:
        """Run a Python script and return success status"""
        full_path = os.path.join(self.project_root, script_path)
        
        if not os.path.exists(full_path):
            print(f"❌ Error: Script not found: {full_path}")
            return False
        
        print(f"🚀 Running: python3 {script_path}")
        start_time = time.time()
        
        try:
            # Run the script
            result = subprocess.run(
                [sys.executable, full_path],
                cwd=self.project_root,
                capture_output=False,  # Let output go directly to terminal
                text=True
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.returncode == 0:
                print(f"✅ {step_name} completed successfully in {duration:.1f}s")
                return True
            else:
                print(f"❌ {step_name} failed with exit code {result.returncode}")
                return False
                
        except Exception as e:
            print(f"❌ Error running {step_name}: {e}")
            return False
    
    def run_pipeline(self, skip_init: bool = False, specific_step: Optional[str] = None, 
                     start_from: Optional[str] = None) -> bool:
        """Run the complete pipeline or specific steps"""
        
        self.print_banner("Music Analysis Ingestion Pipeline")
        print(f"Project Root: {self.project_root}")
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Determine which steps to run
        if specific_step:
            if specific_step not in self.step_map:
                print(f"❌ Unknown step: {specific_step}")
                print(f"Available steps: {list(self.step_map.keys())}")
                return False
            steps_to_run = [self.step_map[specific_step]]
        elif start_from:
            if start_from not in self.step_map:
                print(f"❌ Unknown step: {start_from}")
                print(f"Available steps: {list(self.step_map.keys())}")
                return False
            # Find the index and run from there
            start_idx = next(i for i, step in enumerate(self.steps) if step[0] == start_from)
            steps_to_run = self.steps[start_idx:]
        else:
            steps_to_run = self.steps[:]
        
        # Skip init if requested
        if skip_init and steps_to_run and steps_to_run[0][0] == 'init':
            steps_to_run = steps_to_run[1:]
            print("⏭️  Skipping database initialization as requested")
        
        if not steps_to_run:
            print("⚠️  No steps to run")
            return True
        
        # Run the steps
        total_steps = len(steps_to_run)
        successful_steps = 0
        pipeline_start = time.time()
        
        for i, (step_id, description, script_path) in enumerate(steps_to_run, 1):
            self.print_step_header(i, total_steps, script_path, description)
            
            if self.run_script(script_path, description):
                successful_steps += 1
            else:
                print(f"\n❌ Pipeline failed at step {i}: {description}")
                print("💡 You can resume from this step using:")
                print(f"   python core/ingest/run_full_pipeline.py --from {step_id}")
                return False
        
        # Final summary
        pipeline_end = time.time()
        total_duration = pipeline_end - pipeline_start
        
        self.print_banner("Pipeline Summary")
        print(f"✅ Successfully completed {successful_steps}/{total_steps} steps")
        print(f"⏱️  Total pipeline duration: {total_duration:.1f}s")
        print(f"🎉 Pipeline completed successfully!")
        
        return True
    
    def list_steps(self):
        """List all available steps"""
        self.print_banner("Available Pipeline Steps")
        for i, (step_id, description, script_path) in enumerate(self.steps, 1):
            print(f"{i:2d}. {step_id:10s} - {description:25s} ({script_path})")
    
    def check_dependencies(self) -> bool:
        """Check if all required scripts exist"""
        print("🔍 Checking pipeline dependencies...")
        
        missing_scripts = []
        for step_id, description, script_path in self.steps:
            full_path = os.path.join(self.project_root, script_path)
            if not os.path.exists(full_path):
                missing_scripts.append((step_id, script_path))
        
        if missing_scripts:
            print("❌ Missing required scripts:")
            for step_id, script_path in missing_scripts:
                print(f"   - {script_path}")
            return False
        
        print("✅ All required scripts found")
        return True

def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(
        description='Run the complete music analysis ingestion pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete pipeline
  python core/ingest/run_full_pipeline.py
  
  # Skip database initialization
  python core/ingest/run_full_pipeline.py --skip-init
  
  # Run only a specific step
  python core/ingest/run_full_pipeline.py --step notes
  
  # Start from a specific step
  python core/ingest/run_full_pipeline.py --from intervals
  
  # List all available steps
  python core/ingest/run_full_pipeline.py --list-steps
  
  # Check dependencies
  python core/ingest/run_full_pipeline.py --check-deps
        """
    )
    
    parser.add_argument('--skip-init', action='store_true',
                       help='Skip database initialization step')
    parser.add_argument('--step', 
                       choices=['init', 'pieces', 'notes', 'note_entry', 'intervals', 'ngrams'],
                       help='Run only a specific step')
    parser.add_argument('--from', dest='start_from',
                       choices=['init', 'pieces', 'notes', 'note_entry', 'intervals', 'ngrams'],
                       help='Start pipeline from a specific step')
    parser.add_argument('--list-steps', action='store_true',
                       help='List all available pipeline steps')
    parser.add_argument('--check-deps', action='store_true',
                       help='Check if all required scripts exist')
    
    args = parser.parse_args()
    
    # Create pipeline manager
    pipeline = IngestionPipeline()
    
    # Handle special commands
    if args.list_steps:
        pipeline.list_steps()
        return 0
    
    if args.check_deps:
        if pipeline.check_dependencies():
            print("🎯 Ready to run pipeline!")
            return 0
        else:
            return 1
    
    # Validate arguments
    if args.step and args.start_from:
        print("❌ Cannot use --step and --from together")
        return 1
    
    # Check dependencies before running
    if not pipeline.check_dependencies():
        return 1
    
    # Run the pipeline
    try:
        success = pipeline.run_pipeline(
            skip_init=args.skip_init,
            specific_step=args.step,
            start_from=args.start_from
        )
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user (Ctrl+C)")
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
