#!/usr/bin/env python3
"""
Script to initialize and populate the parameter_sets table with common parameter combinations.
This table stores different combinations of parameters for interval analysis.
"""

import os
import sys
import sqlite3
from typing import List, Dict

# Add the core directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
from db.db import PiecesDB

def create_parameter_sets_table():
    """Create the parameter_sets table if it doesn't exist"""
    db = PiecesDB()
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS parameter_sets (
        parameter_set_id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,       -- 参数组合的描述，如 "4_q_cT"
        kind TEXT NOT NULL,              -- 音程类型: "quality" 或 "diatonic"
        combine_unisons BOOLEAN NOT NULL, -- 是否合并齐音: true 或 false
        number INTEGER NOT NULL,         -- 音程数字: 3-10
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(kind, combine_unisons, number)  -- 确保参数组合唯一
    );
    
    CREATE INDEX IF NOT EXISTS idx_parameter_sets_kind ON parameter_sets(kind);
    CREATE INDEX IF NOT EXISTS idx_parameter_sets_number ON parameter_sets(number);
    CREATE INDEX IF NOT EXISTS idx_parameter_sets_combine_unisons ON parameter_sets(combine_unisons);
    """
    
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.executescript(create_table_sql)
        conn.commit()
        conn.close()
        print("✓ Parameter sets table created successfully")
    except Exception as e:
        print(f"Error creating parameter sets table: {e}")
        if 'conn' in locals():
            conn.close()
        raise

def generate_parameter_combinations() -> List[Dict]:
    """Generate all parameter combinations"""
    combinations = []
    
    # 参数选项
    kinds = ["quality", "diatonic"]
    combine_unisons_options = [True, False]
    numbers = list(range(3, 11))  # 3-10
    
    for kind in kinds:
        for combine_unisons in combine_unisons_options:
            for number in numbers:
                # 生成描述字符串
                # 格式: {number}_{kind_abbrev}_{combine_unisons_abbrev}
                kind_abbrev = "q" if kind == "quality" else "d"
                combine_abbrev = "cT" if combine_unisons else "cF"
                description = f"{number}_{kind_abbrev}_{combine_abbrev}"
                
                combination = {
                    'description': description,
                    'kind': kind,
                    'combine_unisons': combine_unisons,
                    'number': number
                }
                combinations.append(combination)
    
    return combinations

def insert_parameter_combinations(combinations: List[Dict]) -> int:
    """Insert parameter combinations into the database"""
    if not combinations:
        return 0
    
    db = PiecesDB()
    
    insert_sql = """
    INSERT OR IGNORE INTO parameter_sets (description, kind, combine_unisons, number)
    VALUES (?, ?, ?, ?)
    """
    
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        success_count = 0
        for combo in combinations:
            cursor.execute(insert_sql, (
                combo['description'],
                combo['kind'],
                combo['combine_unisons'],
                combo['number']
            ))
            if cursor.rowcount > 0:
                success_count += 1
        
        conn.commit()
        conn.close()
        return success_count
        
    except Exception as e:
        print(f"Error inserting parameter combinations: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return 0

def get_all_parameter_sets() -> List[Dict]:
    """Get all parameter sets from the database"""
    db = PiecesDB()
    
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT parameter_set_id, description, kind, combine_unisons, number
            FROM parameter_sets
            ORDER BY number, kind, combine_unisons
        """)
        
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        parameter_sets = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        return parameter_sets
        
    except Exception as e:
        print(f"Error retrieving parameter sets: {e}")
        if 'conn' in locals():
            conn.close()
        return []

def display_parameter_sets():
    """Display all parameter sets in a formatted table"""
    parameter_sets = get_all_parameter_sets()
    
    if not parameter_sets:
        print("No parameter sets found in database.")
        return
    
    print(f"\n📊 Parameter Sets ({len(parameter_sets)} total)")
    print("=" * 80)
    print(f"{'ID':<4} {'Description':<12} {'Kind':<10} {'Combine Unisons':<15} {'Number':<6}")
    print("-" * 80)
    
    for param_set in parameter_sets:
        combine_str = "True" if param_set['combine_unisons'] else "False"
        print(f"{param_set['parameter_set_id']:<4} "
              f"{param_set['description']:<12} "
              f"{param_set['kind']:<10} "
              f"{combine_str:<15} "
              f"{param_set['number']:<6}")
    
    # 显示统计信息
    print("-" * 80)
    quality_count = sum(1 for p in parameter_sets if p['kind'] == 'quality')
    diatonic_count = sum(1 for p in parameter_sets if p['kind'] == 'diatonic')
    combine_true_count = sum(1 for p in parameter_sets if p['combine_unisons'])
    combine_false_count = sum(1 for p in parameter_sets if not p['combine_unisons'])
    
    print(f"Statistics:")
    print(f"  • Quality intervals: {quality_count}")
    print(f"  • Diatonic intervals: {diatonic_count}")
    print(f"  • Combine unisons = True: {combine_true_count}")
    print(f"  • Combine unisons = False: {combine_false_count}")
    print(f"  • Number range: {min(p['number'] for p in parameter_sets)}-{max(p['number'] for p in parameter_sets)}")

def main():
    """Main function to initialize parameter sets table and populate it"""
    print("🔧 Initializing Parameter Sets")
    print("=" * 50)
    
    # Create table
    print("Creating parameter sets table...")
    create_parameter_sets_table()
    
    # Generate all combinations
    print("Generating parameter combinations...")
    combinations = generate_parameter_combinations()
    print(f"Generated {len(combinations)} parameter combinations")
    
    # Insert combinations
    print("Inserting parameter combinations into database...")
    success_count = insert_parameter_combinations(combinations)
    print(f"✓ Inserted {success_count} new parameter combinations")
    
    # Display results
    display_parameter_sets()
    
    print(f"\n✨ Parameter sets initialization complete!")
    print(f"You can now reference these parameter sets by their ID or description.")

if __name__ == "__main__":
    main()
