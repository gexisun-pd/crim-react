import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { Piece } from '../types';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

interface PieceSelectorProps {
  onPieceSelect?: (piece: Piece | null) => void;
}

const PieceSelector: React.FC<PieceSelectorProps> = ({ onPieceSelect }) => {
  const [pieces, setPieces] = useState<Piece[]>([]);
  const [selectedPieceId, setSelectedPieceId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadPieces = async () => {
      try {
        setLoading(true);
        const response = await apiService.getAllPieces();
        
        if (response.success && response.data) {
          setPieces(response.data);
        } else {
          setError(response.error || 'Failed to load pieces');
        }
      } catch (error) {
        setError('Error connecting to server');
        console.error('Error fetching pieces:', error);
      } finally {
        setLoading(false);
      }
    };

    loadPieces();
  }, []);

  const handleValueChange = (value: string) => {
    setSelectedPieceId(value);
    const selectedPiece = pieces.find(piece => piece.id.toString() === value);
    onPieceSelect?.(selectedPiece || null);
  };

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading pieces...</div>;
  }

  if (error) {
    return (
      <div className="text-sm text-red-600">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="w-full max-w-md">
      <label className="text-sm font-medium mb-2 block">
        Select a Piece
      </label>
      <Select value={selectedPieceId} onValueChange={handleValueChange}>
        <SelectTrigger>
          <SelectValue placeholder="Choose a musical piece..." />
        </SelectTrigger>
        <SelectContent>
          {pieces.map((piece) => (
            <SelectItem key={piece.id} value={piece.id.toString()}>
              <div className="flex flex-col">
                <span className="font-medium">{piece.title}</span>
                <span className="text-xs text-muted-foreground">
                  {piece.composer} • {piece.filename}
                </span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      
      {selectedPieceId && (
        <div className="mt-2 p-2 bg-muted rounded text-sm">
          <strong>Selected:</strong>{' '}
          {pieces.find(p => p.id.toString() === selectedPieceId)?.title}
        </div>
      )}
    </div>
  );
};

export default PieceSelector;