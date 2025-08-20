import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { Piece } from '../types';
import { Combobox, ComboboxOption } from './ui/combobox';

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

  // Convert pieces to combobox options
  const comboboxOptions: ComboboxOption[] = pieces.map((piece) => ({
    value: piece.id.toString(),
    label: piece.title,
    description: `${piece.composer} • ${piece.filename}`
  }));

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
      <Combobox
        options={comboboxOptions}
        value={selectedPieceId}
        onSelect={handleValueChange}
        placeholder="Choose a musical piece..."
        emptyText="No pieces found."
        searchPlaceholder="Search pieces..."
        className="w-full"
      />
    </div>
  );
};

export default PieceSelector;