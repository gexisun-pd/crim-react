#!/usr/bin/env python3
"""
CRIM DataFrames Cache Manager
Manages all CRIM processing results in a structured way

New structure:
cache/
├── pkl/
│   ├── notes/
│   │   ├── set1/
│   │   │   └── piece_key/
│   │   └── set2/
│   │       └── piece_key/
│   ├── melodic_intervals/
│   │   ├── set1/
│   │   │   └── piece_key/
│   │   └── set2/
│   │       └── piece_key/
│   └── other_stages/
└── csv/
    ├── notes/
    │   ├── set1/
    │   │   └── piece_key/
    │   └── set2/
    │       └── piece_key/
    ├── melodic_intervals/
    │   ├── set1/
    │   │   └── piece_key/
    │   └── set2/
    │       └── piece_key/
    └── other_stages/
"""

import os
import json
import pickle
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib

class CrimCacheManager:
    """Manages CRIM DataFrames cache with stage-based organization"""
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            # Assume we're in core/ directory
            project_root = os.path.dirname(os.path.dirname(__file__))
        
        self.project_root = project_root
        self.cache_dir = os.path.join(project_root, 'data', 'crim_cache')
        self.index_file = os.path.join(self.cache_dir, 'cache_index.json')
        
        # Create base directories
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Load or create index
        self.index = self._load_index()
    
    def _load_index(self) -> Dict:
        """Load cache index or create new one"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load cache index: {e}")
        
        return {
            'version': '2.0',
            'created': datetime.now().isoformat(),
            'structure': 'format/stage/set/piece',
            'pieces': {}
        }
    
    def _save_index(self):
        """Save cache index"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache index: {e}")
    
    def _get_piece_key(self, filename: str) -> str:
        """Generate consistent piece key from filename"""
        base_name = os.path.splitext(filename)[0]
        if base_name.endswith('.musicxml'):
            base_name = os.path.splitext(base_name)[0]
        return base_name
    
    def save_stage_cache(self, stage, file_format, set_slug, piece_key, data_dict, metadata):
        """
        Save cache with new directory structure:
        cache/{file_format}/{stage}/{set_slug}/{piece_key}/
        
        Args:
            stage: 'notes', 'melodic_intervals', 'pieces', etc.
            file_format: 'pkl' or 'csv'
            set_slug: set identifier slug (e.g. 'cT', 'cF', 'cT_kq', etc.)
            piece_key: piece identifier
            data_dict: dictionary of dataframes to save
            metadata: metadata dictionary
        """
        # Create directory structure
        stage_dir = os.path.join(self.cache_dir, file_format, stage, set_slug)
        piece_dir = os.path.join(stage_dir, piece_key)
        os.makedirs(piece_dir, exist_ok=True)
        
        # Save dataframes
        for key, df in data_dict.items():
            if file_format == 'pkl':
                df.to_pickle(os.path.join(piece_dir, f'{key}.pkl'))
            elif file_format == 'csv':
                df.to_csv(os.path.join(piece_dir, f'{key}.csv'), index=False)
        
        # Save metadata as JSON
        with open(os.path.join(piece_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Update index
        self._update_index(stage, file_format, set_slug, piece_key, data_dict, metadata)
    
    def load_stage_cache(self, stage, file_format, set_slug, piece_key):
        """
        Load cache from new directory structure
        
        Args:
            stage: 'notes', 'melodic_intervals', 'pieces', etc.
            file_format: 'pkl' or 'csv'
            set_slug: set identifier slug (e.g. 'cT', 'cF', 'cT_kq', etc.)
            piece_key: piece identifier
        """
        stage_dir = os.path.join(self.cache_dir, file_format, stage, set_slug)
        piece_dir = os.path.join(stage_dir, piece_key)
        
        if not os.path.exists(piece_dir):
            return None
        
        try:
            result = {}
            
            # Load all data files
            for filename in os.listdir(piece_dir):
                if filename == 'metadata.json':
                    continue
                    
                file_path = os.path.join(piece_dir, filename)
                key = os.path.splitext(filename)[0]
                
                if file_format == 'pkl' and filename.endswith('.pkl'):
                    result[key] = pd.read_pickle(file_path)
                elif file_format == 'csv' and filename.endswith('.csv'):
                    result[key] = pd.read_csv(file_path)
            
            # Load metadata
            metadata_path = os.path.join(piece_dir, 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    result['metadata'] = json.load(f)
            
            return result
        except Exception as e:
            print(f"Error loading cache for {piece_key}, {stage} set {set_slug}: {e}")
            return None
    
    def has_stage_cache(self, stage, file_format, set_id, piece_key, required_files=None):
        """
        Check if stage cache exists
        
        Args:
            stage: 'notes', 'melodic_intervals', etc.
            file_format: 'pkl' or 'csv'
            set_id: set identifier
            piece_key: piece identifier
            required_files: list of required file keys (without extension)
        """
        stage_dir = os.path.join(self.cache_dir, file_format, stage, f'set{set_id}')
        piece_dir = os.path.join(stage_dir, piece_key)
        
        if not os.path.exists(piece_dir):
            return False
        
        if required_files:
            extension = f'.{file_format}'
            for file_key in required_files:
                file_path = os.path.join(piece_dir, f'{file_key}{extension}')
                if not os.path.exists(file_path):
                    return False
        
        return True
    
    def _update_index(self, stage, file_format, set_id, piece_key, data_dict, metadata):
        """Update cache index"""
        index_key = f"{stage}/set{set_id}/{piece_key}"
        
        if index_key not in self.index['pieces']:
            self.index['pieces'][index_key] = {
                'created': datetime.now().isoformat(),
                'stage': stage,
                'set_id': set_id,
                'piece_key': piece_key,
                'formats': {}
            }
        
        self.index['pieces'][index_key]['formats'][file_format] = {
            'saved': datetime.now().isoformat(),
            'dataframes': {key: {'shape': df.shape, 'columns': list(df.columns)} 
                          for key, df in data_dict.items()},
            'metadata': metadata
        }
        
        self.index['pieces'][index_key]['updated'] = datetime.now().isoformat()
        self._save_index()

    # Backward compatibility and convenience methods for notes
    def save_notes_cache(self, piece_key, notes_df, durations_df, detail_index_df, metadata, note_set_id):
        """Save notes cache (backward compatibility)"""
        data_dict = {
            'notes': notes_df,
            'durations': durations_df,
            'detail_index': detail_index_df
        }
        # Save both pkl and csv formats
        self.save_stage_cache('notes', 'pkl', note_set_id, piece_key, data_dict, metadata)
        self.save_stage_cache('notes', 'csv', note_set_id, piece_key, data_dict, metadata)
    
    def load_notes_cache(self, piece_key, note_set_id, file_format='pkl'):
        """Load notes cache (backward compatibility)"""
        return self.load_stage_cache('notes', file_format, note_set_id, piece_key)
    
    def has_notes_cache(self, piece_key, note_set_id, file_format='pkl'):
        """Check if notes cache exists (backward compatibility)"""
        required_files = ['notes', 'durations', 'detail_index']
        return self.has_stage_cache('notes', file_format, note_set_id, piece_key, required_files)
    
    # General utility methods
    def list_stages(self) -> List[str]:
        """List all cached stages"""
        stages = set()
        for piece_info in self.index['pieces'].values():
            stages.add(piece_info.get('stage'))
        return sorted(list(stages))
    
    def list_sets_for_stage(self, stage: str) -> List[int]:
        """List all sets for a given stage"""
        sets = set()
        for piece_info in self.index['pieces'].values():
            if piece_info.get('stage') == stage:
                sets.add(piece_info.get('set_id'))
        return sorted(list(sets))
    
    def list_pieces_for_stage_set(self, stage: str, set_id: int) -> List[str]:
        """List all pieces for a given stage and set"""
        pieces = []
        for piece_info in self.index['pieces'].values():
            if (piece_info.get('stage') == stage and 
                piece_info.get('set_id') == set_id):
                pieces.append(piece_info.get('piece_key'))
        return sorted(pieces)
    
    def clear_stage_set(self, stage: str, set_id: int) -> bool:
        """Clear all cache for a specific stage and set"""
        try:
            import shutil
            
            # Remove directories for both formats
            for file_format in ['pkl', 'csv']:
                stage_dir = os.path.join(self.cache_dir, file_format, stage, f'set{set_id}')
                if os.path.exists(stage_dir):
                    shutil.rmtree(stage_dir)
            
            # Remove from index
            keys_to_remove = []
            for key, piece_info in self.index['pieces'].items():
                if (piece_info.get('stage') == stage and 
                    piece_info.get('set_id') == set_id):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.index['pieces'][key]
            
            self._save_index()
            return True
            
        except Exception as e:
            print(f"Error clearing stage {stage} set {set_id}: {e}")
            return False
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        stats = {
            'total_pieces': len(self.index['pieces']),
            'stages': {},
            'formats': set(),
            'cache_size_mb': self._get_cache_size_mb()
        }
        
        for piece_info in self.index['pieces'].values():
            stage = piece_info.get('stage')
            set_id = piece_info.get('set_id')
            
            if stage not in stats['stages']:
                stats['stages'][stage] = {}
            if set_id not in stats['stages'][stage]:
                stats['stages'][stage][set_id] = 0
            stats['stages'][stage][set_id] += 1
            
            stats['formats'].update(piece_info.get('formats', {}).keys())
        
        stats['formats'] = sorted(list(stats['formats']))
        return stats
    
    def _get_cache_size_mb(self) -> float:
        """Calculate cache size in MB"""
        total_size = 0
        try:
            for root, dirs, files in os.walk(self.cache_dir):
                for file in files:
                    total_size += os.path.getsize(os.path.join(root, file))
            return round(total_size / (1024 * 1024), 2)
        except:
            return 0.0

# Create global instance
cache_manager = CrimCacheManager()
