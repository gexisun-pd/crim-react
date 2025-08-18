import music21
import os
from typing import Dict, List, Tuple, Optional

class Music21Analyzer:
    """Use music21 to analyze MusicXML files and get accurate note positions"""
    
    @staticmethod
    def get_note_positions_from_musicxml(file_path: str) -> List[Dict]:
        """
        Extract note positions using music21 for accurate onset calculation
        Returns list of note data with accurate onset values
        """
        try:
            print(f"Analyzing {file_path} with music21...")
            
            # Load the score using music21
            score = music21.converter.parse(file_path)
            
            note_positions = []
            
            # Iterate through all parts (voices)
            for part_index, part in enumerate(score.parts):
                voice_id = part_index + 1  # Assuming voice_id starts from 1
                
                print(f"Processing part {voice_id}: {part.partName if hasattr(part, 'partName') else 'Unknown'}")
                
                # Get all notes and rests, but filter appropriately
                for element in part.flatten().notesAndRests:
                    if isinstance(element, music21.note.Note):
                        # Only include actual notes (not rests)
                        note_data = {
                            'voice_id': voice_id,
                            'onset': float(element.offset),
                            'duration': float(element.duration.quarterLength),
                            'pitch_name': element.pitch.name,
                            'midi_note': element.pitch.midi,
                            'octave': element.pitch.octave,
                            'step': element.pitch.step,
                            'alter': element.pitch.accidental.alter if element.pitch.accidental else 0,
                            'type': 'Note'
                        }
                        
                        # Get measure information
                        measure = element.measureNumber
                        if measure:
                            note_data['measure'] = measure
                            
                        # Calculate beat position within measure
                        try:
                            beat_position = element.beat
                            if beat_position:
                                note_data['beat'] = float(beat_position)
                        except:
                            note_data['beat'] = None
                            
                        note_positions.append(note_data)
                        
                    elif isinstance(element, music21.chord.Chord):
                        # Handle chords - each note in chord gets same onset
                        for pitch in element.pitches:
                            note_data = {
                                'voice_id': voice_id,
                                'onset': float(element.offset),
                                'duration': float(element.duration.quarterLength),
                                'pitch_name': pitch.name,
                                'midi_note': pitch.midi,
                                'octave': pitch.octave,
                                'step': pitch.step,
                                'alter': pitch.accidental.alter if pitch.accidental else 0,
                                'type': 'Note'
                            }
                            
                            # Get measure information
                            measure = element.measureNumber
                            if measure:
                                note_data['measure'] = measure
                                
                            try:
                                beat_position = element.beat
                                if beat_position:
                                    note_data['beat'] = float(beat_position)
                            except:
                                note_data['beat'] = None
                                
                            note_positions.append(note_data)
                            
                    # Skip rests for now since database might not include them
                    # elif isinstance(element, music21.note.Rest):
                    #     # Include rests for completeness
                    #     rest_data = {
                    #         'voice_id': voice_id,
                    #         'onset': float(element.offset),
                    #         'duration': float(element.duration.quarterLength),
                    #         'pitch_name': None,
                    #         'midi_note': None,
                    #         'octave': None,
                    #         'step': None,
                    #         'alter': 0,
                    #         'type': 'Rest'
                    #     }
                    #     
                    #     measure = element.measureNumber
                    #     if measure:
                    #         rest_data['measure'] = measure
                    #         
                    #     try:
                    #         beat_position = element.beat
                    #         if beat_position:
                    #             rest_data['beat'] = float(beat_position)
                    #     except:
                    #         rest_data['beat'] = None
                    #         
                    #     note_positions.append(rest_data)
            
            # Sort by onset, then by voice_id
            note_positions.sort(key=lambda x: (x['onset'], x['voice_id']))
            
            print(f"Extracted {len(note_positions)} notes from music21 analysis (excluding rests)")
            return note_positions
            
        except Exception as e:
            print(f"Error analyzing {file_path} with music21: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def create_svg_to_database_mapping(file_path: str, piece_id: int, 
                                     database_notes: List[Dict]) -> Dict[int, Dict]:
        """
        Create mapping between SVG note order and database note_id
        using accurate music21 onset calculations
        """
        try:
            print(f"Creating SVG mapping for piece {piece_id}...")
            
            # Get accurate positions from music21
            music21_notes = Music21Analyzer.get_note_positions_from_musicxml(file_path)
            
            if not music21_notes:
                print("No music21 notes found")
                return {}
            
            print(f"Found {len(music21_notes)} music21 notes, {len(database_notes)} database notes")
            
            mapping = {}
            
            # Match music21 notes with database notes
            for svg_index, m21_note in enumerate(music21_notes):
                # Skip rests for mapping (they don't usually have corresponding database entries)
                if m21_note['type'] == 'Rest':
                    continue
                    
                # Find best match in database notes
                best_match = None
                min_distance = float('inf')
                
                for db_note in database_notes:
                    # Calculate distance based on onset, voice, and pitch
                    onset_diff = abs(m21_note['onset'] - db_note['onset'])
                    voice_diff = 0 if m21_note['voice_id'] == db_note['voice'] else 100
                    
                    # Pitch matching
                    pitch_diff = 0
                    if m21_note.get('midi_note') and db_note.get('pitch'):
                        pitch_diff = abs(m21_note['midi_note'] - db_note['pitch'])
                    elif m21_note.get('pitch_name') and db_note.get('name'):
                        # Basic name matching
                        if m21_note['pitch_name'] not in db_note['name']:
                            pitch_diff = 10
                    
                    total_distance = onset_diff + voice_diff + pitch_diff
                    
                    if total_distance < min_distance:
                        min_distance = total_distance
                        best_match = db_note
                
                # Only include matches with reasonable confidence
                if best_match and min_distance < 5.0:  # Reasonable threshold
                    mapping[svg_index] = {
                        'note_id': best_match['note_id'],
                        'onset': m21_note['onset'],
                        'voice_id': m21_note['voice_id'],
                        'pitch_name': m21_note['pitch_name'],
                        'midi_note': m21_note.get('midi_note'),
                        'octave': m21_note.get('octave'),
                        'measure': m21_note.get('measure'),
                        'beat': m21_note.get('beat'),
                        'duration': m21_note['duration'],
                        'database_onset': best_match['onset'],
                        'database_voice': best_match['voice'],
                        'database_name': best_match['name'],
                        'match_distance': min_distance
                    }
                    
                    print(f"SVG index {svg_index}: {m21_note['pitch_name']} @ onset {m21_note['onset']} -> note_id {best_match['note_id']} (distance: {min_distance:.3f})")
            
            print(f"Created mapping for {len(mapping)} notes")
            return mapping
            
        except Exception as e:
            print(f"Error creating mapping: {e}")
            import traceback
            traceback.print_exc()
            return {}

    @staticmethod
    def get_note_at_svg_index(file_path: str, svg_index: int) -> Optional[Dict]:
        """
        Get music21 note data at specific SVG index
        """
        try:
            music21_notes = Music21Analyzer.get_note_positions_from_musicxml(file_path)
            
            if svg_index < 0 or svg_index >= len(music21_notes):
                return None
                
            return music21_notes[svg_index]
            
        except Exception as e:
            print(f"Error getting note at SVG index {svg_index}: {e}")
            return None
