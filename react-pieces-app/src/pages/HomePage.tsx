import React, { useState } from 'react';
import PieceSelector from '../components/PieceSelector';
import ScoreViewer from '../components/ScoreViewer';
import { Piece } from '../types';

const HomePage: React.FC = () => {
  const [selectedPiece, setSelectedPiece] = useState<Piece | null>(null);

  const handlePieceSelect = (piece: Piece | null) => {
    setSelectedPiece(piece);
  };

  const handleNoteClick = (noteId: string, element: Element) => {
    console.log('Note clicked:', noteId, element);
    // TODO: 在这里添加与数据库交互的逻辑
    // 例如：获取音符信息、更新状态、显示详情等
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-foreground">
            Musical Pieces Analysis
          </h1>
          <p className="text-muted-foreground">
            Select a piece from the database to view and interact with the score
          </p>
        </div>

        {/* Piece Selector */}
        <div className="bg-card rounded-lg p-6 border">
          <PieceSelector onPieceSelect={handlePieceSelect} />
        </div>

        {/* Score Viewer */}
        <ScoreViewer 
          piece={selectedPiece} 
          onNoteClick={handleNoteClick}
          className="min-h-[600px]"
        />

        {/* Selected Piece Info */}
        {selectedPiece && (
          <div className="bg-card rounded-lg p-6 border">
            <h3 className="text-lg font-semibold mb-4">Selected Piece Details</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground">Title</label>
                <p className="text-lg">{selectedPiece.title}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Composer</label>
                <p className="text-lg">{selectedPiece.composer}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Filename</label>
                <p className="text-sm font-mono bg-muted px-2 py-1 rounded">
                  {selectedPiece.filename}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Piece ID</label>
                <p className="text-sm">{selectedPiece.id}</p>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center text-sm text-muted-foreground">
          <p>Click on any note in the score to interact with the database</p>
        </div>
      </div>
    </div>
  );
};

export default HomePage;