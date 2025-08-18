import os
import sys
import pandas as pd
from typing import Dict, List, Tuple, Optional

# Import crim_intervals for consistent analysis
try:
    import crim_intervals
    from crim_intervals import CorpusBase
    CRIM_INTERVALS_AVAILABLE = True
except ImportError:
    print("Warning: crim_intervals library not available")
    CRIM_INTERVALS_AVAILABLE = False

class Music21Analyzer:
    """Use crim_intervals to analyze MusicXML files and get accurate note positions (same as database ingestion)"""
    
    @staticmethod
    def get_note_positions_from_musicxml(file_path: str) -> List[Dict]:
        """
        Extract note positions using crim_intervals for consistent analysis
        Same method as database ingestion, but always with combineUnisons=False
        """
        if not CRIM_INTERVALS_AVAILABLE:
            print("Error: crim_intervals library is required for analysis")
            return []
            
        try:
            print(f"Analyzing {file_path} with crim_intervals (combineUnisons=False)...")
            
            # Create a corpus with just this piece - same as database ingestion
            corpus = CorpusBase([file_path])
            
            # Access the piece from corpus.scores
            if not hasattr(corpus, 'scores') or len(corpus.scores) == 0:
                print(f"Error: No scores found in corpus")
                return []
            
            piece = corpus.scores[0]
            
            # Get notes with combineUnisons=False (always False for frontend analysis)
            notes_df = piece.notes(combineUnisons=False)
            
            if notes_df.empty:
                print(f"Warning: No notes found in {file_path}")
                return []
            
            # Get durations DataFrame
            durations_df = piece.durations()
            
            # Use detailIndex to get measure and beat information
            detail_df = piece.detailIndex(notes_df, measure=True, beat=True, offset=True)
            
            print(f"Found {detail_df.shape[0]} time points with {len([col for col in detail_df.columns if col not in ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']])} voices")
            
            # Convert to list format similar to database ingestion
            note_positions = []
            
            # Get voice columns (exclude metadata columns)
            metadata_cols = ['Measure', 'Beat', 'Offset', 'Composer', 'Title', 'Date']
            voice_columns = [col for col in detail_df.columns if col not in metadata_cols]
            
            # Iterate through each row (time point)
            for idx, row in detail_df.iterrows():
                # Extract timing information - handle different index types
                if isinstance(idx, tuple):
                    # Multi-index case
                    offset = idx[0] if len(idx) > 0 else 0.0
                else:
                    # Single index case
                    offset = idx
                
                # Get measure and beat from columns
                measure = row.get('Measure') if 'Measure' in detail_df.columns else None
                beat = row.get('Beat') if 'Beat' in detail_df.columns else None
                
                # Get duration for this offset
                duration = 0.0
                try:
                    if offset in durations_df.index:
                        duration_row = durations_df.loc[offset]
                        # Get the first non-null duration value from any voice
                        if isinstance(duration_row, pd.Series):
                            for voice_col in voice_columns:
                                if voice_col in duration_row and pd.notna(duration_row[voice_col]):
                                    duration = float(duration_row[voice_col])
                                    break
                        elif isinstance(duration_row, (int, float)):
                            duration = float(duration_row)
                except Exception as e:
                    print(f"Warning: Could not get duration for offset {offset}: {e}")
                    duration = 0.0
                
                # Process each voice at this time point
                for voice_idx, voice_name in enumerate(voice_columns, 1):
                    note_value = row[voice_name]
                    
                    # Skip NaN, empty, or None values
                    if pd.isna(note_value) or note_value == '' or note_value is None:
                        continue
                    
                    # Skip rests for SVG mapping (they usually don't appear in SVG)
                    if str(note_value).strip() == "Rest":
                        continue
                    
                    # Parse note information
                    pitch = None
                    name = str(note_value)
                    step = None
                    octave = None
                    alter = 0
                    
                    # Try to parse the note name (e.g., "A4", "C#5", "Bb3")
                    try:
                        note_str = str(note_value).strip()
                        if len(note_str) >= 2:
                            # Extract step (note name)
                            step = note_str[0].upper()
                            
                            # Extract alterations
                            alter = 0
                            if '#' in note_str:
                                alter = 1
                            elif 'b' in note_str or '♭' in note_str:
                                alter = -1
                            
                            # Extract octave
                            octave_str = ''.join(filter(str.isdigit, note_str))
                            octave = int(octave_str) if octave_str else None
                            
                            # Convert to MIDI pitch if we have all components
                            if step and octave is not None:
                                step_to_midi = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
                                base_pitch = step_to_midi.get(step, 0)
                                pitch = (octave + 1) * 12 + base_pitch + alter
                    except Exception as e:
                        print(f"Warning: Could not parse note '{note_value}': {e}")
                    
                    # Create note data
                    note_data = {
                        'voice_id': voice_idx,
                        'voice_name': voice_name,
                        'onset': float(offset),
                        'duration': duration,
                        'pitch_name': name,
                        'midi_note': pitch,
                        'octave': octave,
                        'step': step,
                        'alter': alter,
                        'type': 'Note',
                        'measure': int(measure) if measure is not None and pd.notna(measure) else None,
                        'beat': float(beat) if beat is not None and pd.notna(beat) else None
                    }
                    
                    note_positions.append(note_data)
            
            # Sort by onset, then by voice_id (same as SVG rendering order)
            note_positions.sort(key=lambda x: (x['onset'], x['voice_id']))
            
            print(f"Extracted {len(note_positions)} notes from crim_intervals analysis (excluding rests)")
            return note_positions
            
        except Exception as e:
            print(f"Error analyzing {file_path} with crim_intervals: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def create_svg_to_database_mapping(file_path: str, piece_id: int, 
                                     database_notes: List[Dict]) -> Dict[int, Dict]:
        """
        Create mapping between SVG note order and database note_id
        using crim_intervals analysis (consistent with database ingestion)
        """
        try:
            print(f"Creating SVG mapping for piece {piece_id}...")
            
            # Get accurate positions from crim_intervals (combineUnisons=False)
            crim_notes = Music21Analyzer.get_note_positions_from_musicxml(file_path)
            
            if not crim_notes:
                print("No crim_intervals notes found")
                return {}
            
            print(f"Found {len(crim_notes)} crim_intervals notes, {len(database_notes)} database notes")
            
            mapping = {}
            
            # Match crim_intervals notes with database notes
            for svg_index, crim_note in enumerate(crim_notes):
                # Find best match in database notes
                best_match = None
                min_distance = float('inf')
                
                for db_note in database_notes:
                    # Calculate distance based on onset, voice, and pitch
                    onset_diff = abs(crim_note['onset'] - db_note['onset'])
                    voice_diff = 0 if crim_note['voice_id'] == db_note['voice'] else 100
                    
                    # Pitch matching
                    pitch_diff = 0
                    if crim_note.get('midi_note') and db_note.get('pitch'):
                        pitch_diff = abs(crim_note['midi_note'] - db_note['pitch'])
                    elif crim_note.get('pitch_name') and db_note.get('name'):
                        # Basic name matching
                        if crim_note['pitch_name'] not in db_note['name']:
                            pitch_diff = 10
                    
                    total_distance = onset_diff + voice_diff + pitch_diff
                    
                    if total_distance < min_distance:
                        min_distance = total_distance
                        best_match = db_note
                
                # Only include matches with reasonable confidence
                if best_match and min_distance < 5.0:  # Reasonable threshold
                    mapping[svg_index] = {
                        'note_id': best_match['note_id'],
                        'onset': crim_note['onset'],
                        'voice_id': crim_note['voice_id'],
                        'pitch_name': crim_note['pitch_name'],
                        'midi_note': crim_note.get('midi_note'),
                        'octave': crim_note.get('octave'),
                        'measure': crim_note.get('measure'),
                        'beat': crim_note.get('beat'),
                        'duration': crim_note['duration'],
                        'database_onset': best_match['onset'],
                        'database_voice': best_match['voice'],
                        'database_name': best_match['name'],
                        'match_distance': min_distance
                    }
                    
                    print(f"SVG index {svg_index}: {crim_note['pitch_name']} @ onset {crim_note['onset']} -> note_id {best_match['note_id']} (distance: {min_distance:.3f})")
            
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
        Get crim_intervals note data at specific SVG index
        """
        try:
            crim_notes = Music21Analyzer.get_note_positions_from_musicxml(file_path)
            
            if svg_index < 0 or svg_index >= len(crim_notes):
                return None
                
            return crim_notes[svg_index]
            
        except Exception as e:
            print(f"Error getting note at SVG index {svg_index}: {e}")
            return None
