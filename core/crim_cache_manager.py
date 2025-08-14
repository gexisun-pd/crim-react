#!/usr/bin/env python3
"""
CRIM DataFrames Cache Manager
Manages all CRIM processing results in a structured way
"""

import os
import json
import pickle
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib

class CrimCacheManager:
    """Manages CRIM DataFrames cache with versioning and metadata"""
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            # Assume we're in core/ directory
            project_root = os.path.dirname(os.path.dirname(__file__))
        
        self.project_root = project_root
        self.cache_root = os.path.join(project_root, 'data', 'crim_cache')
        self.pieces_dir = os.path.join(self.cache_root, 'pieces')
        self.csv_dir = os.path.join(self.cache_root, 'csv_exports')
        self.index_file = os.path.join(self.cache_root, 'cache_index.json')
        
        # Create directories
        os.makedirs(self.pieces_dir, exist_ok=True)
        os.makedirs(self.csv_dir, exist_ok=True)
        
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
            'version': '1.0',
            'created': datetime.now().isoformat(),
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
    
    def _get_piece_dir(self, piece_key: str) -> str:
        """Get piece directory path"""
        return os.path.join(self.pieces_dir, piece_key)
    
    def _get_csv_dir(self, piece_key: str) -> str:
        """Get CSV export directory path"""
        return os.path.join(self.csv_dir, piece_key)
    
    def save_dataframe(self, piece_key: str, df_type: str, df: pd.DataFrame, 
                      metadata: Dict = None) -> bool:
        """Save a DataFrame with metadata"""
        try:
            piece_dir = self._get_piece_dir(piece_key)
            csv_piece_dir = self._get_csv_dir(piece_key)
            os.makedirs(piece_dir, exist_ok=True)
            os.makedirs(csv_piece_dir, exist_ok=True)
            
            # Save as pickle
            pkl_file = os.path.join(piece_dir, f"{df_type}.pkl")
            df.to_pickle(pkl_file)
            
            # Save as CSV for human readability
            csv_file = os.path.join(csv_piece_dir, f"{df_type}.csv")
            df.to_csv(csv_file)
            
            # Update index
            if piece_key not in self.index['pieces']:
                self.index['pieces'][piece_key] = {
                    'created': datetime.now().isoformat(),
                    'dataframes': {}
                }
            
            self.index['pieces'][piece_key]['dataframes'][df_type] = {
                'saved': datetime.now().isoformat(),
                'shape': df.shape,
                'columns': list(df.columns),
                'metadata': metadata or {}
            }
            
            self.index['pieces'][piece_key]['updated'] = datetime.now().isoformat()
            self._save_index()
            
            return True
            
        except Exception as e:
            print(f"Error saving DataFrame {df_type} for {piece_key}: {e}")
            return False
    
    def load_dataframe(self, piece_key: str, df_type: str) -> Optional[pd.DataFrame]:
        """Load a DataFrame"""
        try:
            pkl_file = os.path.join(self._get_piece_dir(piece_key), f"{df_type}.pkl")
            if os.path.exists(pkl_file):
                return pd.read_pickle(pkl_file)
            return None
        except Exception as e:
            print(f"Error loading DataFrame {df_type} for {piece_key}: {e}")
            return None
    
    def has_dataframe(self, piece_key: str, df_type: str) -> bool:
        """Check if a DataFrame exists"""
        if piece_key not in self.index['pieces']:
            return False
        return df_type in self.index['pieces'][piece_key].get('dataframes', {})
    
    def get_piece_info(self, piece_key: str) -> Optional[Dict]:
        """Get information about a cached piece"""
        return self.index['pieces'].get(piece_key)
    
    def list_pieces(self) -> List[str]:
        """List all cached pieces"""
        return list(self.index['pieces'].keys())
    
    def list_dataframes(self, piece_key: str) -> List[str]:
        """List all DataFrames for a piece"""
        if piece_key not in self.index['pieces']:
            return []
        return list(self.index['pieces'][piece_key].get('dataframes', {}).keys())
    
    def remove_piece(self, piece_key: str) -> bool:
        """Remove all data for a piece"""
        try:
            import shutil
            
            # Remove directories
            piece_dir = self._get_piece_dir(piece_key)
            csv_dir = self._get_csv_dir(piece_key)
            
            if os.path.exists(piece_dir):
                shutil.rmtree(piece_dir)
            if os.path.exists(csv_dir):
                shutil.rmtree(csv_dir)
            
            # Remove from index
            if piece_key in self.index['pieces']:
                del self.index['pieces'][piece_key]
                self._save_index()
            
            return True
            
        except Exception as e:
            print(f"Error removing piece {piece_key}: {e}")
            return False
    
    def clear_all(self) -> bool:
        """Clear all cached data"""
        try:
            import shutil
            
            if os.path.exists(self.cache_root):
                shutil.rmtree(self.cache_root)
            
            # Recreate structure
            os.makedirs(self.pieces_dir, exist_ok=True)
            os.makedirs(self.csv_dir, exist_ok=True)
            
            # Reset index
            self.index = {
                'version': '1.0',
                'created': datetime.now().isoformat(),
                'pieces': {}
            }
            self._save_index()
            
            return True
            
        except Exception as e:
            print(f"Error clearing cache: {e}")
            return False
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        total_pieces = len(self.index['pieces'])
        total_dataframes = 0
        df_types = set()
        
        for piece_info in self.index['pieces'].values():
            dataframes = piece_info.get('dataframes', {})
            total_dataframes += len(dataframes)
            df_types.update(dataframes.keys())
        
        return {
            'total_pieces': total_pieces,
            'total_dataframes': total_dataframes,
            'dataframe_types': sorted(list(df_types)),
            'cache_size_mb': self._get_cache_size_mb()
        }
    
    def _get_cache_size_mb(self) -> float:
        """Calculate cache size in MB"""
        total_size = 0
        try:
            for root, dirs, files in os.walk(self.cache_root):
                for file in files:
                    total_size += os.path.getsize(os.path.join(root, file))
            return round(total_size / (1024 * 1024), 2)
        except:
            return 0.0

# Create global instance
cache_manager = CrimCacheManager()
