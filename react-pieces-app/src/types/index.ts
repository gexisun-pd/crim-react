export interface Piece {
  id: number;
  filename: string;
  path: string;
  title: string;
  composer: string;
  date_created?: string;
  date_updated?: string;
}

export interface NoteSet {
  id: number;
  slug: string;
  combine_unisons: boolean;
  description: string;
}

export interface Note {
  note_id: number;
  onset: number;
  voice_id: number;
  voice_name?: string;
  pitch_name?: string;
  midi_note?: number;
  is_entry: boolean;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  count?: number;
}