import React, { useState } from 'react';
import PieceSelector from '../components/PieceSelector';
import SimpleOSMD from '../components/SimpleOSMD';
import NoteAnalyzer from '../components/NoteAnalyzer';
import { Piece } from '../types';

const PieceViewer: React.FC = () => {
  const [selectedPiece, setSelectedPiece] = useState<Piece | null>(null);
  const [osmdNoteInfo, setOsmdNoteInfo] = useState<any>(null); // OSMD原始数据
  const [analysisResult, setAnalysisResult] = useState<any>(null); // 分析结果

  const handlePieceSelect = (piece: Piece | null) => {
    setSelectedPiece(piece);
    setOsmdNoteInfo(null); // 清除之前选择的音符
    setAnalysisResult(null); // 清除分析结果
  };

  const handleNoteClick = (osmdNoteInfo: any) => {
    console.log('Note clicked in PieceViewer:', osmdNoteInfo);
    setOsmdNoteInfo(osmdNoteInfo);
  };

  const handleAnalysisComplete = (result: any) => {
    setAnalysisResult(result);
  };

  return (
    <div className="h-full bg-background p-4">
      <div className="max-w-full mx-auto h-full">
        {/* Three Column Layout */}
        <div className="grid grid-cols-12 gap-4 h-[calc(100vh-60px)]">
          {/* Left Panel - Piece Selection & Info */}
          <div className="col-span-2 bg-card rounded-lg border p-3 overflow-y-auto">
            <div className="space-y-3">
              {/* Piece Selector */}
              <div>
                <h3 className="text-sm font-semibold mb-2">Select Piece</h3>
                <PieceSelector onPieceSelect={handlePieceSelect} />
              </div>

              {/* Selected Piece Info */}
              {selectedPiece && (
                <div>
                  <h3 className="text-sm font-semibold mb-2">Piece Information</h3>
                  <div className="space-y-2 text-xs">
                    <div>
                      <label className="font-medium text-muted-foreground">Title</label>
                      <p className="text-foreground">{selectedPiece.title}</p>
                    </div>
                    <div>
                      <label className="font-medium text-muted-foreground">Composer</label>
                      <p className="text-foreground">{selectedPiece.composer}</p>
                    </div>
                    <div>
                      <label className="font-medium text-muted-foreground">Filename</label>
                      <p className="text-xs font-mono bg-muted px-1 py-0.5 rounded break-all">
                        {selectedPiece.filename}
                      </p>
                    </div>
                    <div>
                      <label className="font-medium text-muted-foreground">ID</label>
                      <p className="text-xs">{selectedPiece.id}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Middle Panel - Score Display */}
          <div className="col-span-7 bg-card rounded-lg border overflow-y-auto">
            <SimpleOSMD 
              piece={selectedPiece} 
              onNoteClick={handleNoteClick}
            />
          </div>

          {/* Right Panel - Note Analysis */}
          <div className="col-span-3 bg-card rounded-lg border p-3 overflow-y-auto">
            <NoteAnalyzer 
              piece={selectedPiece}
              osmdNoteInfo={osmdNoteInfo}
              onAnalysisComplete={handleAnalysisComplete}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default PieceViewer;
