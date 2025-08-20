from flask import Blueprint, jsonify, request, send_file
import os
import sys

# Add the core directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'core'))

from db.db import PiecesDB

# Add the api directory to the path for local imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.music21_analyzer import Music21Analyzer
from utils.music21_analyzer import Music21Analyzer

pieces_bp = Blueprint('pieces', __name__)

@pieces_bp.route('/pieces', methods=['GET'])
def get_all_pieces():
    """Get all pieces from the database"""
    try:
        db = PiecesDB()
        pieces = db.get_all_pieces()
        
        # Transform the data for frontend consumption
        pieces_data = []
        for piece in pieces:
            pieces_data.append({
                'id': piece['piece_id'],
                'filename': piece['filename'],
                'path': piece['path'],
                'title': piece.get('title', piece['filename']),  # Use filename as fallback title
                'composer': piece.get('composer', 'Unknown'),
                'date_created': piece.get('date_created'),
                'date_updated': piece.get('date_updated')
            })
        
        return jsonify({
            'success': True,
            'data': pieces_data,
            'count': len(pieces_data)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pieces_bp.route('/pieces/<int:piece_id>', methods=['GET'])
def get_piece_by_id(piece_id):
    """Get a specific piece by ID"""
    try:
        db = PiecesDB()
        piece = db.get_piece_by_id(piece_id)
        
        if not piece:
            return jsonify({
                'success': False,
                'error': 'Piece not found'
            }), 404
        
        piece_data = {
            'id': piece['piece_id'],
            'filename': piece['filename'],
            'path': piece['path'],
            'title': piece.get('title', piece['filename']),
            'composer': piece.get('composer', 'Unknown'),
            'date_created': piece.get('date_created'),
            'date_updated': piece.get('date_updated')
        }
        
        return jsonify({
            'success': True,
            'data': piece_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pieces_bp.route('/note-sets', methods=['GET'])
def get_all_note_sets():
    """Get all note sets from the database"""
    try:
        db = PiecesDB()
        note_sets = db.get_all_note_sets()
        
        # Transform the data for frontend consumption
        note_sets_data = []
        for note_set in note_sets:
            note_sets_data.append({
                'id': note_set['set_id'],
                'slug': note_set['slug'],
                'combine_unisons': bool(note_set['combine_unisons']),
                'description': f"{'With' if note_set['combine_unisons'] else 'Without'} unisons"
            })
        
        return jsonify({
            'success': True,
            'data': note_sets_data,
            'count': len(note_sets_data)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pieces_bp.route('/pieces/<int:piece_id>/notes', methods=['GET'])
def get_piece_notes(piece_id):
    """Get notes for a specific piece and note set"""
    try:
        note_set_id = request.args.get('note_set_id', 1, type=int)
        
        db = PiecesDB()
        
        # Verify piece exists
        piece = db.get_piece_by_id(piece_id)
        if not piece:
            return jsonify({
                'success': False,
                'error': 'Piece not found'
            }), 404
        
        # Get notes for this piece and note set
        notes = db.get_notes_for_piece_and_set(piece_id, note_set_id)
        
        # Transform the data
        notes_data = []
        for note in notes:
            notes_data.append({
                'note_id': note['note_id'],
                'onset': note['onset'],
                'voice_id': note['voice_id'],
                'voice_name': note.get('voice_name'),
                'pitch_name': note.get('pitch_name'),
                'midi_note': note.get('midi_note'),
                'is_entry': bool(note.get('is_entry', False))
            })
        
        return jsonify({
            'success': True,
            'data': notes_data,
            'piece_id': piece_id,
            'note_set_id': note_set_id,
            'count': len(notes_data)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pieces_bp.route('/pieces/<int:piece_id>/musicxml', methods=['GET'])
def get_piece_musicxml(piece_id):
    """Get the MusicXML content for a specific piece"""
    try:
        db = PiecesDB()
        piece = db.get_piece_by_id(piece_id)
        
        if not piece:
            return jsonify({
                'success': False,
                'error': 'Piece not found'
            }), 404
        
        # Get the file path and make it absolute
        file_path = piece.get('path')
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'No file path found for this piece'
            }), 404
        
        # Convert to absolute path (assuming files are in data/ directory)
        if not os.path.isabs(file_path):
            base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
            file_path = os.path.join(base_path, file_path)
        
        file_path = os.path.normpath(file_path)
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': f'MusicXML file not found at: {file_path}'
            }), 404
        
        # Read and return the MusicXML content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                musicxml_content = f.read()
            
            return musicxml_content, 200, {'Content-Type': 'application/xml'}
            
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            with open(file_path, 'r', encoding='latin-1') as f:
                musicxml_content = f.read()
            
            return musicxml_content, 200, {'Content-Type': 'application/xml'}
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pieces_bp.route('/notes/<int:note_id>/details', methods=['GET'])
def get_note_details(note_id):
    """Get detailed information for a specific note by note_id"""
    try:
        db = PiecesDB()
        note_details = db.get_note_by_id(note_id)
        
        if not note_details:
            return jsonify({
                'success': False,
                'error': 'Note not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': note_details
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pieces_bp.route('/pieces/<int:piece_id>/svg-mapping', methods=['GET'])
def get_svg_note_mapping(piece_id):
    """Get accurate SVG to database note mapping using music21"""
    try:
        note_set_id = request.args.get('note_set_id', 1, type=int)
        
        db = PiecesDB()
        
        # Get piece info
        piece = db.get_piece_by_id(piece_id)
        if not piece:
            return jsonify({
                'success': False,
                'error': 'Piece not found'
            }), 404
        
        # Get database notes
        db_notes = db.get_notes_for_piece(piece_id, note_set_id)
        
        # Get file path
        file_path = piece.get('path')
        if not os.path.isabs(file_path):
            base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
            file_path = os.path.join(base_path, file_path)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': f'MusicXML file not found: {file_path}'
            }), 404
        
        print(f"Creating SVG mapping for piece {piece_id}, file: {file_path}")
        
        # Create accurate mapping using music21
        mapping = Music21Analyzer.create_svg_to_database_mapping(
            file_path, piece_id, db_notes
        )
        
        return jsonify({
            'success': True,
            'mapping': mapping,
            'piece_id': piece_id,
            'note_set_id': note_set_id,
            'svg_notes_count': len(mapping),
            'database_notes_count': len(db_notes)
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pieces_bp.route('/pieces/<int:piece_id>/notes/find-by-position', methods=['POST'])
def find_note_by_svg_position(piece_id):
    """Find note by measure, beat, voice and note_set_id"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data required'
            }), 400
        
        measure = data.get('measure')
        beat = data.get('beat')
        voice = data.get('voice')
        note_set_id = data.get('note_set_id', 1)
        tolerance = data.get('tolerance', 0.25)  # beat tolerance
        
        if measure is None or beat is None or voice is None:
            return jsonify({
                'success': False,
                'error': 'measure, beat, and voice are required'
            }), 400
        
        db = PiecesDB()
        
        # Verify piece exists
        piece = db.get_piece_by_id(piece_id)
        if not piece:
            return jsonify({
                'success': False,
                'error': 'Piece not found'
            }), 404
        
        # Search for match using direct SQL query with beat tolerance
        import sqlite3
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        db_path = os.path.join(project_root, 'database', 'analysis.db')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query for position-based match with tolerance
        cursor.execute("""
            SELECT note_id, piece_id, note_set_id, voice, voice_name, onset, duration, 
                   offset, measure, beat, pitch, name, step, octave, `alter`, type, staff, tie,
                   ABS(beat - ?) as beat_distance
            FROM notes 
            WHERE piece_id = ? AND note_set_id = ? AND voice = ? AND measure = ? 
              AND ABS(beat - ?) <= ?
            ORDER BY beat_distance ASC
            LIMIT 1
        """, (beat, piece_id, note_set_id, voice, measure, beat, tolerance))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Convert row to dictionary
            columns = ['note_id', 'piece_id', 'note_set_id', 'voice', 'voice_name', 
                      'onset', 'duration', 'offset', 'measure', 'beat', 'pitch', 
                      'name', 'step', 'octave', 'alter', 'type', 'staff', 'tie', 'beat_distance']
            note = dict(zip(columns, row))
            
            # Remove the beat_distance from the result
            del note['beat_distance']
            
            return jsonify({
                'success': True,
                'note': note,
                'search_criteria': {
                    'piece_id': piece_id,
                    'note_set_id': note_set_id,
                    'measure': measure,
                    'beat': beat,
                    'voice': voice,
                    'tolerance': tolerance,
                    'match_type': 'position_based'
                }
            })
        else:
            return jsonify({
                'success': True,
                'note': None,
                'message': f'No match found for piece_id={piece_id}, note_set_id={note_set_id}, measure={measure}, beat={beat}, voice={voice} (tolerance={tolerance})',
                'search_criteria': {
                    'piece_id': piece_id,
                    'note_set_id': note_set_id,
                    'measure': measure,
                    'beat': beat,
                    'voice': voice,
                    'tolerance': tolerance,
                    'match_type': 'position_based'
                }
            })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pieces_bp.route('/pieces/<int:piece_id>/notes/find-exact', methods=['POST'])
def find_exact_note_match(piece_id):
    """Find exact note match in database for given onset, voice, and note_set_id"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data required'
            }), 400
        
        onset = data.get('onset')
        voice = data.get('voice')
        note_set_id = data.get('note_set_id', 1)
        
        if onset is None or voice is None:
            return jsonify({
                'success': False,
                'error': 'onset and voice are required'
            }), 400
        
        db = PiecesDB()
        
        # Verify piece exists
        piece = db.get_piece_by_id(piece_id)
        if not piece:
            return jsonify({
                'success': False,
                'error': 'Piece not found'
            }), 404
        
        # Search for exact match using direct SQL query
        import sqlite3
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        db_path = os.path.join(project_root, 'database', 'analysis.db')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query for exact match
        cursor.execute("""
            SELECT note_id, piece_id, note_set_id, voice, voice_name, onset, duration, 
                   offset, measure, beat, pitch, name, step, octave, `alter`, type, staff, tie
            FROM notes 
            WHERE piece_id = ? AND note_set_id = ? AND voice = ? AND onset = ?
        """, (piece_id, note_set_id, voice, onset))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Convert row to dictionary
            columns = ['note_id', 'piece_id', 'note_set_id', 'voice', 'voice_name', 
                      'onset', 'duration', 'offset', 'measure', 'beat', 'pitch', 
                      'name', 'step', 'octave', 'alter', 'type', 'staff', 'tie']
            note = dict(zip(columns, row))
            
            return jsonify({
                'success': True,
                'note': note,
                'search_criteria': {
                    'piece_id': piece_id,
                    'note_set_id': note_set_id,
                    'voice': voice,
                    'onset': onset,
                    'exact_match': True
                }
            })
        else:
            return jsonify({
                'success': True,
                'note': None,
                'message': f'No exact match found for piece_id={piece_id}, note_set_id={note_set_id}, voice={voice}, onset={onset}',
                'search_criteria': {
                    'piece_id': piece_id,
                    'note_set_id': note_set_id,
                    'voice': voice,
                    'onset': onset,
                    'exact_match': True
                }
            })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pieces_bp.route('/pieces/<int:piece_id>/notes/search-by-osmd', methods=['POST'])
def search_notes_by_osmd_data(piece_id):
    """Search notes in both note sets using OSMD extracted measure, beat, and part data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data required'
            }), 400
        
        measure = data.get('measure')
        beat = data.get('beat') 
        part_id = data.get('part_id') or data.get('voice')  # 支持两种字段名
        tolerance = data.get('tolerance', 0.25)  # beat tolerance
        
        if measure is None or beat is None or part_id is None:
            return jsonify({
                'success': False,
                'error': 'measure, beat, and part_id (or voice) are required'
            }), 400
        
        db = PiecesDB()
        
        # Verify piece exists
        piece = db.get_piece_by_id(piece_id)
        if not piece:
            return jsonify({
                'success': False,
                'error': 'Piece not found'
            }), 404
        
        # Search in both note sets
        import sqlite3
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        db_path = os.path.join(project_root, 'database', 'analysis.db')
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()
        
        results = {}
        
        # Search in note_set 1 (combine_unisons = True)
        cursor.execute("""
            SELECT * FROM notes 
            WHERE piece_id = ? AND note_set_id = 1 AND voice = ? AND measure = ? 
              AND ABS(beat - ?) <= ?
            ORDER BY ABS(beat - ?) ASC
            LIMIT 1
        """, (piece_id, part_id, measure, beat, tolerance, beat))
        
        row = cursor.fetchone()
        if row:
            results['note_set_1'] = dict(row)
        else:
            results['note_set_1'] = None
        
        # Search in note_set 2 (combine_unisons = False)  
        cursor.execute("""
            SELECT * FROM notes 
            WHERE piece_id = ? AND note_set_id = 2 AND voice = ? AND measure = ? 
              AND ABS(beat - ?) <= ?
            ORDER BY ABS(beat - ?) ASC
            LIMIT 1
        """, (piece_id, part_id, measure, beat, tolerance, beat))
        
        row = cursor.fetchone()
        if row:
            results['note_set_2'] = dict(row)
        else:
            results['note_set_2'] = None
        
        conn.close()
        
        return jsonify({
            'success': True,
            'database_matches': results,
            'search_criteria': {
                'piece_id': piece_id,
                'measure': measure,
                'beat': beat,
                'part_id': part_id,
                'voice': part_id,  # 保持兼容性
                'tolerance': tolerance,
                'search_type': 'osmd_position_based'
            },
            'osmd_analysis': {
                'measure': measure,
                'beat': beat,
                'part_id': part_id,
                'extraction_method': 'osmd_api'
            }
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pieces_bp.route('/notes/<int:note_id>/melodic-ngrams', methods=['GET'])
def get_melodic_ngrams_by_note_id(note_id):
    """Get melodic ngrams that start from a specific note_id"""
    try:
        db = PiecesDB()
        
        # First verify the note exists
        note = db.get_note_by_id(note_id)
        if not note:
            return jsonify({
                'success': False,
                'error': 'Note not found'
            }), 404
        
        # Search for melodic ngrams starting from this note
        import sqlite3
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        db_path = os.path.join(project_root, 'database', 'analysis.db')
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get melodic ngrams with set information
        cursor.execute("""
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
                mns.slug as ngram_set_slug,
                mns.description as ngram_set_description,
                mns.ngrams_number,
                mis.kind as interval_kind,
                ns.combine_unisons,
                ns.slug as note_set_slug
            FROM melodic_ngrams mn
            JOIN melodic_ngram_sets mns ON mn.melodic_ngram_set_id = mns.set_id
            JOIN melodic_interval_sets mis ON mns.melodic_interval_set_id = mis.set_id
            JOIN note_sets ns ON mis.note_set_id = ns.set_id
            WHERE mn.note_id = ?
            ORDER BY mns.set_id, mn.onset
        """, (note_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Group results by melodic ngram set
        ngrams_by_set = {}
        for row in rows:
            set_id = row['melodic_ngram_set_id']
            if set_id not in ngrams_by_set:
                ngrams_by_set[set_id] = {
                    'melodic_ngram_set_id': set_id,
                    'ngram_set_slug': row['ngram_set_slug'],
                    'ngram_set_description': row['ngram_set_description'],
                    'ngrams_number': row['ngrams_number'],
                    'interval_kind': row['interval_kind'],
                    'combine_unisons': bool(row['combine_unisons']),
                    'note_set_slug': row['note_set_slug'],
                    'ngrams': []
                }
            
            ngrams_by_set[set_id]['ngrams'].append({
                'ngram_id': row['ngram_id'],
                'piece_id': row['piece_id'],
                'note_id': row['note_id'],
                'voice': row['voice'],
                'voice_name': row['voice_name'],
                'onset': row['onset'],
                'ngram': row['ngram'],
                'ngram_length': row['ngram_length']
            })
        
        return jsonify({
            'success': True,
            'note_id': note_id,
            'note_info': dict(note),
            'melodic_ngrams': list(ngrams_by_set.values()),
            'total_sets': len(ngrams_by_set),
            'total_ngrams': sum(len(set_data['ngrams']) for set_data in ngrams_by_set.values())
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pieces_bp.route('/notes/batch-melodic-ngrams', methods=['POST'])
def get_melodic_ngrams_for_multiple_notes():
    """Get melodic ngrams for multiple note_ids"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data required'
            }), 400
        
        note_ids = data.get('note_ids', [])
        if not note_ids or not isinstance(note_ids, list):
            return jsonify({
                'success': False,
                'error': 'note_ids array is required'
            }), 400
        
        # Limit to prevent excessive queries
        if len(note_ids) > 10:
            return jsonify({
                'success': False,
                'error': 'Maximum 10 note_ids allowed per request'
            }), 400
        
        import sqlite3
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        db_path = os.path.join(project_root, 'database', 'analysis.db')
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        results = {}
        
        for note_id in note_ids:
            # Verify note exists and get basic info
            cursor.execute("SELECT * FROM notes WHERE note_id = ?", (note_id,))
            note = cursor.fetchone()
            
            if not note:
                results[note_id] = {
                    'success': False,
                    'error': 'Note not found',
                    'note_info': None,
                    'melodic_ngrams': []
                }
                continue
            
            # Get melodic ngrams for this note
            cursor.execute("""
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
                    mns.slug as ngram_set_slug,
                    mns.description as ngram_set_description,
                    mns.ngrams_number,
                    mis.kind as interval_kind,
                    ns.combine_unisons,
                    ns.slug as note_set_slug
                FROM melodic_ngrams mn
                JOIN melodic_ngram_sets mns ON mn.melodic_ngram_set_id = mns.set_id
                JOIN melodic_interval_sets mis ON mns.melodic_interval_set_id = mis.set_id
                JOIN note_sets ns ON mis.note_set_id = ns.set_id
                WHERE mn.note_id = ?
                ORDER BY mns.set_id, mn.onset
            """, (note_id,))
            
            rows = cursor.fetchall()
            
            # Group by melodic ngram set
            ngrams_by_set = {}
            for row in rows:
                set_id = row['melodic_ngram_set_id']
                if set_id not in ngrams_by_set:
                    ngrams_by_set[set_id] = {
                        'melodic_ngram_set_id': set_id,
                        'ngram_set_slug': row['ngram_set_slug'],
                        'ngram_set_description': row['ngram_set_description'],
                        'ngrams_number': row['ngrams_number'],
                        'interval_kind': row['interval_kind'],
                        'combine_unisons': bool(row['combine_unisons']),
                        'note_set_slug': row['note_set_slug'],
                        'ngrams': []
                    }
                
                ngrams_by_set[set_id]['ngrams'].append({
                    'ngram_id': row['ngram_id'],
                    'piece_id': row['piece_id'],
                    'note_id': row['note_id'],
                    'voice': row['voice'],
                    'voice_name': row['voice_name'],
                    'onset': row['onset'],
                    'ngram': row['ngram'],
                    'ngram_length': row['ngram_length']
                })
            
            results[note_id] = {
                'success': True,
                'note_info': dict(note),
                'melodic_ngrams': list(ngrams_by_set.values()),
                'total_sets': len(ngrams_by_set),
                'total_ngrams': sum(len(set_data['ngrams']) for set_data in ngrams_by_set.values())
            }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'results': results,
            'processed_note_ids': note_ids
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
