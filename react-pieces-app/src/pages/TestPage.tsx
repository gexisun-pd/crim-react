import React, { useState } from 'react';
import PieceSelector from '../components/PieceSelector';
import SimpleOSMD from '../components/SimpleOSMD';
import { Piece } from '../types';

const TestPage: React.FC = () => {
  const [selectedPiece, setSelectedPiece] = useState<Piece | null>(null);
  const [selectedNoteDetails, setSelectedNoteDetails] = useState<any>(null);

  const handlePieceSelect = (piece: Piece | null) => {
    setSelectedPiece(piece);
    setSelectedNoteDetails(null); // 清除之前选择的音符
  };

  const handleNoteClick = (noteDetails: any) => {
    console.log('Note clicked in TestPage:', noteDetails);
    setSelectedNoteDetails(noteDetails);
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-foreground">
            OSMD Test Page - Musical Pieces Analysis
          </h1>
          <p className="text-muted-foreground">
            Using SimpleOSMD component for reliable score rendering
          </p>
        </div>

        {/* Piece Selector */}
        <div className="bg-card rounded-lg p-6 border">
          <PieceSelector onPieceSelect={handlePieceSelect} />
        </div>

        {/* Simple OSMD Score Viewer */}
        <div className="bg-card rounded-lg border">
          <SimpleOSMD 
            piece={selectedPiece} 
            onNoteClick={handleNoteClick}
          />
        </div>

        {/* Selected Note Details */}
        {selectedNoteDetails && (
          <div className="bg-card rounded-lg p-6 border">
            <h3 className="text-lg font-semibold mb-4">Selected Note Analysis</h3>
            
            {/* OSMD Analysis Section */}
            {selectedNoteDetails.osmd_analysis && (
              <div className="mb-6 p-4 bg-blue-50 rounded-lg">
                <h4 className="text-md font-semibold mb-3 text-blue-800">OSMD 位置分析</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <label className="text-sm font-medium text-blue-600">Measure</label>
                    <p className="text-lg font-mono">{selectedNoteDetails.osmd_analysis.measure}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-blue-600">Beat</label>
                    <p className="text-lg font-mono">{selectedNoteDetails.osmd_analysis.beat}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-blue-600">Voice</label>
                    <p className="text-lg">{selectedNoteDetails.osmd_analysis.voice}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-blue-600">Method</label>
                    <p className="text-xs">{selectedNoteDetails.osmd_analysis.extraction_method}</p>
                  </div>
                </div>
                {selectedNoteDetails.osmd_analysis.element_index !== undefined && (
                  <div className="mt-2">
                    <label className="text-sm font-medium text-blue-600">Element Index</label>
                    <p className="text-sm">{selectedNoteDetails.osmd_analysis.element_index}</p>
                  </div>
                )}
              </div>
            )}

            {/* Element Info */}
            <div className="mb-4 p-4 bg-gray-50 rounded-lg">
              <h4 className="text-md font-semibold mb-3">Element Information</h4>
              <div className="space-y-2">
                <div>
                  <label className="text-sm font-medium text-gray-600">Element ID</label>
                  <p className="text-sm font-mono bg-white px-2 py-1 rounded border">
                    {selectedNoteDetails.element_id || 'N/A'}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-600">Element Class</label>
                  <p className="text-sm font-mono bg-white px-2 py-1 rounded border">
                    {selectedNoteDetails.element_class || 'N/A'}
                  </p>
                </div>
                {selectedNoteDetails.message && (
                  <div>
                    <label className="text-sm font-medium text-gray-600">Message</label>
                    <p className="text-sm">{selectedNoteDetails.message}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

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
          <p>Click on any note in the score to interact with the system</p>
          <p className="mt-1">This page uses SimpleOSMD component based on the successful test implementation</p>
        </div>
      </div>
    </div>
  );
};

export default TestPage;
