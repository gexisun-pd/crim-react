import React, { useState } from 'react';
import PieceSelector from '../components/PieceSelector';
import SimpleOSMD from '../components/SimpleOSMD';
import { Piece } from '../types';

const PieceViewer: React.FC = () => {
  const [selectedPiece, setSelectedPiece] = useState<Piece | null>(null);
  const [selectedNoteDetails, setSelectedNoteDetails] = useState<any>(null);

  const handlePieceSelect = (piece: Piece | null) => {
    setSelectedPiece(piece);
    setSelectedNoteDetails(null); // 清除之前选择的音符
  };

  const handleNoteClick = (noteDetails: any) => {
    console.log('Note clicked in PieceViewer:', noteDetails);
    setSelectedNoteDetails(noteDetails);
  };

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="max-w-full mx-auto">
        {/* Header */}
        <div className="text-center mb-4">
          <h1 className="text-2xl font-bold text-foreground">Music Analysis Viewer</h1>
          <p className="text-sm text-muted-foreground">分析音乐作品的小节、拍子和声部信息</p>
        </div>

        {/* Three Column Layout */}
        <div className="grid grid-cols-12 gap-4 h-[calc(100vh-140px)]">
          {/* Left Panel - Piece Selection & Info */}
          <div className="col-span-2 bg-card rounded-lg border p-3 overflow-y-auto">
            <div className="space-y-3">
              {/* Piece Selector */}
              <div>
                <h3 className="text-sm font-semibold mb-2">选择曲目</h3>
                <PieceSelector onPieceSelect={handlePieceSelect} />
              </div>

              {/* Selected Piece Info */}
              {selectedPiece && (
                <div>
                  <h3 className="text-sm font-semibold mb-2">曲目信息</h3>
                  <div className="space-y-2 text-xs">
                    <div>
                      <label className="font-medium text-muted-foreground">标题</label>
                      <p className="text-foreground">{selectedPiece.title}</p>
                    </div>
                    <div>
                      <label className="font-medium text-muted-foreground">作曲家</label>
                      <p className="text-foreground">{selectedPiece.composer}</p>
                    </div>
                    <div>
                      <label className="font-medium text-muted-foreground">文件名</label>
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
            <h3 className="text-sm font-semibold mb-3">音符分析</h3>
            
            {selectedNoteDetails ? (
              <div className="space-y-3">
                {/* OSMD Analysis */}
                {selectedNoteDetails.osmd_analysis && (
                  <div className="p-2 bg-blue-50 rounded text-xs">
                    <h4 className="font-semibold mb-2 text-blue-800">OSMD 分析</h4>
                    <div className="space-y-1">
                      <div className="flex justify-between">
                        <span className="text-blue-600">小节:</span>
                        <span className="font-mono">{selectedNoteDetails.osmd_analysis.measure}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-blue-600">拍子:</span>
                        <span className="font-mono">{selectedNoteDetails.osmd_analysis.beat}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-blue-600">声部ID:</span>
                        <span className="font-mono">{selectedNoteDetails.osmd_analysis.part_id}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-blue-600">声部名:</span>
                        <span className="text-xs">{selectedNoteDetails.osmd_analysis.part_name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-blue-600">音高:</span>
                        <span className="text-xs">{selectedNoteDetails.osmd_analysis.pitch}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-blue-600">时值:</span>
                        <span className="text-xs">{selectedNoteDetails.osmd_analysis.duration}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Database Matches */}
                {selectedNoteDetails.database_matches && (
                  <div className="space-y-2">
                    <h4 className="font-semibold text-xs">数据库匹配</h4>
                    
                    {/* Note Set 1 */}
                    <div className="p-2 border rounded text-xs">
                      <h5 className="font-medium mb-1 text-green-700">Note Set 1</h5>
                      {selectedNoteDetails.database_matches.note_set_1 ? (
                        <div className="space-y-1">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">ID:</span>
                            <span className="font-mono text-xs">{selectedNoteDetails.database_matches.note_set_1.note_id}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">音名:</span>
                            <span className="text-xs">{selectedNoteDetails.database_matches.note_set_1.name}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">起始:</span>
                            <span className="font-mono text-xs">{selectedNoteDetails.database_matches.note_set_1.onset}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">声部:</span>
                            <span className="text-xs">{selectedNoteDetails.database_matches.note_set_1.voice}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">音高:</span>
                            <span className="text-xs">{selectedNoteDetails.database_matches.note_set_1.pitch}</span>
                          </div>
                        </div>
                      ) : (
                        <p className="text-muted-foreground text-xs">未找到匹配</p>
                      )}
                    </div>

                    {/* Note Set 2 */}
                    <div className="p-2 border rounded text-xs">
                      <h5 className="font-medium mb-1 text-purple-700">Note Set 2</h5>
                      {selectedNoteDetails.database_matches.note_set_2 ? (
                        <div className="space-y-1">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">ID:</span>
                            <span className="font-mono text-xs">{selectedNoteDetails.database_matches.note_set_2.note_id}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">音名:</span>
                            <span className="text-xs">{selectedNoteDetails.database_matches.note_set_2.name}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">起始:</span>
                            <span className="font-mono text-xs">{selectedNoteDetails.database_matches.note_set_2.onset}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">声部:</span>
                            <span className="text-xs">{selectedNoteDetails.database_matches.note_set_2.voice}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">音高:</span>
                            <span className="text-xs">{selectedNoteDetails.database_matches.note_set_2.pitch}</span>
                          </div>
                        </div>
                      ) : (
                        <p className="text-muted-foreground text-xs">未找到匹配</p>
                      )}
                    </div>
                  </div>
                )}

                {/* Search Criteria */}
                {selectedNoteDetails.search_criteria && (
                  <div className="p-2 bg-gray-50 rounded text-xs">
                    <h5 className="font-medium mb-1">搜索条件</h5>
                    <div className="space-y-1">
                      <div>小节: <code className="text-xs">{selectedNoteDetails.search_criteria.measure}</code></div>
                      <div>拍子: <code className="text-xs">{selectedNoteDetails.search_criteria.beat}</code></div>
                      <div>声部: <code className="text-xs">{selectedNoteDetails.search_criteria.part || selectedNoteDetails.search_criteria.voice}</code></div>
                    </div>
                  </div>
                )}

                {/* Error Information */}
                {selectedNoteDetails.error && (
                  <div className="p-2 bg-red-50 border border-red-200 rounded text-xs">
                    <p className="text-red-600">错误: {selectedNoteDetails.error}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center text-muted-foreground text-xs mt-8">
                <p>点击乐谱中的音符来查看分析结果</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PieceViewer;
