from flask import Blueprint, jsonify, request, send_file
import os
import sys

# Add the core directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'core'))

from db.db import PiecesDB

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

@pieces_bp.route('/pieces/<int:piece_id>/note-mapping', methods=['GET'])
def get_piece_note_mapping(piece_id):
    """Get SVG-to-database note mapping for a piece"""
    try:
        db = PiecesDB()
        piece = db.get_piece_by_id(piece_id)
        
        if not piece:
            return jsonify({
                'success': False,
                'error': f'Piece with ID {piece_id} not found'
            }), 404
        
        # Get database notes ordered by onset and voice
        notes_db = db.get_notes_for_piece(piece_id)
        
        if not notes_db:
            return jsonify({
                'success': False,
                'error': f'No notes found for piece {piece_id}'
            }), 404
        
        # Create mapping data structure
        # This maps SVG note order to database note information
        mapping_data = []
        
        # Filter out rest notes and sort by onset, then by voice
        note_notes = [note for note in notes_db if note.get('type') == 'Note']
        note_notes.sort(key=lambda x: (x.get('onset', 0), x.get('voice', 1)))
        
        for svg_index, note in enumerate(note_notes):
            mapping_data.append({
                'svg_index': svg_index,
                'note_id': note['note_id'],
                'piece_id': piece_id,
                'voice': note.get('voice', 1),
                'voice_name': note.get('voice_name', ''),
                'onset': note.get('onset', 0),
                'measure': note.get('measure', 1),
                'pitch_name': note.get('name', ''),
                'octave': note.get('octave'),
                'duration': note.get('duration', 0)
            })
        
        return jsonify({
            'success': True,
            'data': {
                'piece_id': piece_id,
                'total_notes': len(mapping_data),
                'mapping': mapping_data
            }
        })
        
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
