# 数据库函数包装器，用于 FastAPI 集成
import sys
import os

# 确保可以导入核心模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

def get_all_pieces_from_db():
    """获取所有音乐作品"""
    try:
        from db.db import PiecesDB
        
        db = PiecesDB()
        pieces = db.get_all_pieces()
        
        # 转换字段名以匹配React组件的期望
        normalized_pieces = []
        for piece in pieces:
            normalized_pieces.append({
                'id': piece.get('piece_id'),  # 映射 piece_id 到 id
                'title': piece.get('title'),
                'composer': piece.get('composer'),
                'filename': piece.get('filename'),
                'path': piece.get('path'),
                'date_created': piece.get('created_at'),
                'date_updated': piece.get('updated_at')
            })
        
        return {
            'success': True,
            'data': normalized_pieces,
            'count': len(normalized_pieces)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'count': 0
        }

def get_piece_by_id_from_db(piece_id: int):
    """根据ID获取特定音乐作品"""
    try:
        from db.db import PiecesDB
        
        db = PiecesDB()
        piece = db.get_piece_by_id(piece_id)
        
        if piece:
            # 转换字段名
            normalized_piece = {
                'id': piece.get('piece_id'),
                'title': piece.get('title'),
                'composer': piece.get('composer'),
                'filename': piece.get('filename'),
                'path': piece.get('path'),
                'date_created': piece.get('created_at'),
                'date_updated': piece.get('updated_at')
            }
            
            return {
                'success': True,
                'data': normalized_piece
            }
        else:
            return None
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def get_all_note_sets_from_db():
    """获取所有音符集合"""
    try:
        from db.db import PiecesDB
        
        db = PiecesDB()
        note_sets = db.get_all_note_sets()
        
        return {
            'success': True,
            'data': note_sets,
            'count': len(note_sets)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'count': 0
        }

def get_notes_for_piece_from_db(piece_id: int, note_set_id: int = 1):
    """获取作品的音符数据"""
    try:
        from db.db import PiecesDB
        
        db = PiecesDB()
        notes = db.get_notes_for_piece_and_set(piece_id, note_set_id)
        
        return {
            'success': True,
            'data': notes,
            'count': len(notes)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'count': 0
        }
