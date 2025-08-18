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

@pieces_bp.route('/notes/find-by-position', methods=['POST'])
def find_note_by_position():
    """Find note_id by piece_id, voice, and onset position"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data required'
            }), 400
        
        piece_id = data.get('piece_id')
        voice = data.get('voice') 
        onset = data.get('onset')
        tolerance = data.get('tolerance', 0.001)
        
        if piece_id is None or voice is None or onset is None:
            return jsonify({
                'success': False,
                'error': 'piece_id, voice, and onset are required'
            }), 400
        
        # Use the existing NoteIdUpdater functionality
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'core', 'utils'))
        from note_id_updater import NoteIdUpdater
        
        updater = NoteIdUpdater()
        note_id = updater.find_note_id(piece_id, voice, onset, tolerance)
        
        if note_id is None:
            return jsonify({
                'success': False,
                'error': f'No note found for piece_id={piece_id}, voice={voice}, onset={onset}'
            }), 404
        
        # Get detailed note information
        db = PiecesDB()
        note_details = db.get_note_by_id(note_id)
        
        if not note_details:
            return jsonify({
                'success': False,
                'error': f'Note details not found for note_id={note_id}'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'note_id': note_id,
                'search_params': {
                    'piece_id': piece_id,
                    'voice': voice,
                    'onset': onset,
                    'tolerance': tolerance
                },
                'note_details': note_details
            }
        })
    
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

@pieces_bp.route('/pieces/<int:piece_id>/analyze-with-music21', methods=['POST'])
def analyze_piece_with_music21(piece_id):
    """Analyze piece with music21 and return note at specific SVG position"""
    try:
        data = request.get_json()
        svg_index = data.get('svg_index')
        
        if svg_index is None:
            return jsonify({
                'success': False,
                'error': 'svg_index is required'
            }), 400
        
        db = PiecesDB()
        piece = db.get_piece_by_id(piece_id)
        
        if not piece:
            return jsonify({
                'success': False,
                'error': 'Piece not found'
            }), 404
        
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
        
        # Use music21 to get note at specific position
        target_note = Music21Analyzer.get_note_at_svg_index(file_path, svg_index)
        
        if not target_note:
            return jsonify({
                'success': False,
                'error': f'SVG index {svg_index} out of range or invalid'
            }), 400
        
        # Find corresponding note in database using the existing NoteIdUpdater
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'core', 'utils'))
        from note_id_updater import NoteIdUpdater
        
        note_id_updater = NoteIdUpdater()
        note_id = note_id_updater.find_note_id(
            piece_id=piece_id,
            voice=target_note['voice_id'],
            onset=target_note['onset'],
            tolerance=0.1  # More generous tolerance
        )
        
        if note_id:
            # Get full note details
            note_details = db.get_note_by_id(note_id)
            if note_details:
                # Add music21 analysis data
                note_details.update({
                    'music21_onset': target_note['onset'],
                    'music21_duration': target_note['duration'],
                    'music21_measure': target_note.get('measure'),
                    'music21_beat': target_note.get('beat'),
                    'music21_pitch_name': target_note.get('pitch_name'),
                    'svg_index': svg_index
                })
                
                return jsonify({
                    'success': True,
                    'data': note_details
                })
        
        return jsonify({
            'success': False,
            'error': f'Could not match SVG note {svg_index} with database',
            'music21_data': target_note
        }), 404
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
