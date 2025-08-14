import sqlite3
import os
from typing import Dict, List

class PiecesDB:
    def __init__(self, db_path=None):
        if db_path is None:
            # Get project root directory (three levels up from core/db/)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(project_root, 'database', 'analysis.db')
        self.db_path = db_path
    
    def insert_piece(self, piece_data: Dict) -> int:
        """Insert a single piece into the database and return the piece_id"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO pieces (path, filename, title, composer, sha256)
                VALUES (?, ?, ?, ?, ?)
            """, (
                piece_data['path'],
                piece_data['filename'],
                piece_data.get('title'),
                piece_data.get('composer'),
                piece_data.get('sha256')
            ))
            
            piece_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"Inserted piece: {piece_data['filename']} (ID: {piece_id})")
            return piece_id
            
        except sqlite3.Error as e:
            print(f"Database error inserting {piece_data['filename']}: {e}")
            if conn:
                conn.close()
            return None
        except Exception as e:
            print(f"Unexpected error inserting {piece_data['filename']}: {e}")
            if conn:
                conn.close()
            return None
    
    def insert_pieces_batch(self, pieces_list: List[Dict]) -> int:
        """Insert multiple pieces in a batch and return number of successful insertions"""
        success_count = 0
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for piece_data in pieces_list:
                try:
                    cursor.execute("""
                        INSERT INTO pieces (path, filename, title, composer, sha256)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        piece_data['path'],
                        piece_data['filename'],
                        piece_data.get('title'),
                        piece_data.get('composer'),
                        piece_data.get('sha256')
                    ))
                    success_count += 1
                    print(f"Inserted piece: {piece_data['filename']}")
                except sqlite3.Error as e:
                    print(f"Error inserting {piece_data['filename']}: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            if conn:
                conn.close()
        except Exception as e:
            print(f"Unexpected error during batch insert: {e}")
            if conn:
                conn.close()
        
        return success_count
    
    def piece_exists(self, path: str, filename: str) -> bool:
        """Check if a piece already exists in the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM pieces WHERE path = ? AND filename = ?
            """, (path, filename))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count > 0
            
        except sqlite3.Error as e:
            print(f"Database error checking existence: {e}")
            if conn:
                conn.close()
            return False
    
    def get_all_pieces(self) -> List[Dict]:
        """Get all pieces from the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM pieces")
            rows = cursor.fetchall()
            
            columns = [description[0] for description in cursor.description]
            pieces = [dict(zip(columns, row)) for row in rows]
            
            conn.close()
            return pieces
            
        except sqlite3.Error as e:
            print(f"Database error retrieving pieces: {e}")
            if conn:
                conn.close()
            return []
    
    def notes_exist_for_piece(self, piece_id: int) -> bool:
        """Check if notes already exist for a piece"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM notes WHERE piece_id = ?", (piece_id,))
            count = cursor.fetchone()[0]
            conn.close()
            
            return count > 0
            
        except sqlite3.Error as e:
            print(f"Database error checking notes existence: {e}")
            if conn:
                conn.close()
            return False
    
    def insert_notes_batch(self, notes_list: List[Dict]) -> int:
        """Insert multiple notes in a batch and return number of successful insertions"""
        success_count = 0
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for note_data in notes_list:
                try:
                    cursor.execute("""
                        INSERT INTO notes (
                            piece_id, voice, voice_name, onset, duration, measure, beat, 
                            pitch, name, step, octave, `alter`, type, staff, tie
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        note_data['piece_id'],
                        note_data.get('voice'),
                        note_data.get('voice_name'),
                        note_data.get('onset'),
                        note_data.get('duration'),
                        note_data.get('measure'),
                        note_data.get('beat'),
                        note_data.get('pitch'),
                        note_data.get('name'),
                        note_data.get('step'),
                        note_data.get('octave'),
                        note_data.get('alter'),
                        note_data.get('type'),
                        note_data.get('staff'),
                        note_data.get('tie')
                    ))
                    success_count += 1
                except sqlite3.Error as e:
                    print(f"Error inserting note for piece {note_data['piece_id']}: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error as e:
            print(f"Database connection error during notes insertion: {e}")
            if conn:
                conn.close()
        except Exception as e:
            print(f"Unexpected error during notes batch insert: {e}")
            if conn:
                conn.close()
        
        return success_count
    
    def get_notes_for_piece(self, piece_id: int) -> List[Dict]:
        """Get all notes for a specific piece"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM notes WHERE piece_id = ? ORDER BY onset", (piece_id,))
            rows = cursor.fetchall()
            
            columns = [description[0] for description in cursor.description]
            notes = [dict(zip(columns, row)) for row in rows]
            
            conn.close()
            return notes
            
        except sqlite3.Error as e:
            print(f"Database error retrieving notes for piece {piece_id}: {e}")
            if conn:
                conn.close()
            return []
