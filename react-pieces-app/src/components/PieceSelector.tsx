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
        setError(null);
        
        console.log('开始加载pieces数据...');
        const response = await apiService.getAllPieces();
        console.log('API响应:', response);
        
        if (response && response.success && response.data) {
          console.log('成功获取pieces:', response.data.length, '个');
          setPieces(Array.isArray(response.data) ? response.data : []);
        } else {
          const errorMsg = response?.error || 'API返回错误数据格式';
          console.error('API错误:', errorMsg);
          setError(errorMsg);
          setPieces([]); // 确保pieces为空数组而不是undefined
        }
      } catch (error) {
        const errorMsg = 'API服务器连接失败 - 请确保API服务器在端口9000运行';
        console.error('连接错误:', error);
        setError(errorMsg);
        setPieces([]); // 确保pieces为空数组
      } finally {
        setLoading(false);
      }
    };

    loadPieces();
  }, []);

  const handleValueChange = (value: string) => {
    setSelectedPieceId(value);
    const selectedPiece = pieces.find(piece => piece.id?.toString() === value);
    onPieceSelect?.(selectedPiece || null);
  };

  // Convert pieces to combobox options - with safety checks
  const comboboxOptions: ComboboxOption[] = pieces
    .filter((piece) => piece && piece.id && piece.title) // 过滤掉无效数据
    .map((piece) => ({
      value: piece.id.toString(),
      label: piece.title || 'Untitled',
      description: `${piece.composer || 'Unknown'} • ${piece.filename || 'Unknown file'}`
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