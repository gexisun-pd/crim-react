import { Piece, NoteSet, Note, ApiResponse } from '../types';

const API_BASE_URL = 'http://localhost:9000/api';

class ApiService {
  private async request<T>(endpoint: string): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('API request failed:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
  }

  async getAllPieces(): Promise<ApiResponse<Piece[]>> {
    return this.request<Piece[]>('/pieces');
  }

  async getPieceById(id: number): Promise<ApiResponse<Piece>> {
    return this.request<Piece>(`/pieces/${id}`);
  }

  async getAllNoteSets(): Promise<ApiResponse<NoteSet[]>> {
    return this.request<NoteSet[]>('/note-sets');
  }

  async getPieceNotes(pieceId: number, noteSetId: number = 1): Promise<ApiResponse<Note[]>> {
    return this.request<Note[]>(`/pieces/${pieceId}/notes?note_set_id=${noteSetId}`);
  }

  async checkHealth(): Promise<ApiResponse<{ status: string; service: string }>> {
    try {
      const response = await fetch('http://localhost:9000/health');
      const data = await response.json();
      return {
        success: response.ok,
        data: data
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Health check failed'
      };
    }
  }

  async getPieceMusicXML(pieceId: number): Promise<string | null> {
    try {
      const response = await fetch(`${API_BASE_URL}/pieces/${pieceId}/musicxml`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.text();
    } catch (error) {
      console.error('Failed to fetch MusicXML:', error);
      return null;
    }
  }
}

export const apiService = new ApiService();