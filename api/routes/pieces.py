from flask import Blueprint, jsonify, request
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
