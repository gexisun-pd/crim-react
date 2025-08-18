import React, { useState } from 'react';
import PieceSelector from '../components/PieceSelector';
import ScoreViewer from '../components/ScoreViewer';
import { Piece } from '../types';

const HomePage: React.FC = () => {
  const [selectedPiece, setSelectedPiece] = useState<Piece | null>(null);
  const [selectedNoteDetails, setSelectedNoteDetails] = useState<any>(null);

  const handlePieceSelect = (piece: Piece | null) => {
    setSelectedPiece(piece);
    setSelectedNoteDetails(null); // 清除之前选择的音符
  };

  const handleNoteClick = (noteDetails: any) => {
    console.log('Note clicked in HomePage:', noteDetails);
    setSelectedNoteDetails(noteDetails);
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

        {/* Selected Note Details */}
        {selectedNoteDetails && (
          <div className="bg-card rounded-lg p-6 border">
            <h3 className="text-lg font-semibold mb-4">Selected Note Analysis</h3>
            
            {/* Music21 Analysis Section */}
            {selectedNoteDetails.music21_analysis && (
              <div className="mb-6 p-4 bg-blue-50 rounded-lg">
                <h4 className="text-md font-semibold mb-3 text-blue-800">Music21 中间层分析</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <label className="text-sm font-medium text-blue-600">Onset</label>
                    <p className="text-lg font-mono">{selectedNoteDetails.music21_analysis.onset}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-blue-600">Voice ID</label>
                    <p className="text-lg">{selectedNoteDetails.music21_analysis.voice_id}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-blue-600">Pitch Name</label>
                    <p className="text-lg">{selectedNoteDetails.music21_analysis.pitch_name}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-blue-600">Duration</label>
                    <p className="text-lg">{selectedNoteDetails.music21_analysis.duration}</p>
                  </div>
                  {selectedNoteDetails.music21_analysis.measure && (
                    <div>
                      <label className="text-sm font-medium text-blue-600">Measure</label>
                      <p className="text-lg">{selectedNoteDetails.music21_analysis.measure}</p>
                    </div>
                  )}
                  {selectedNoteDetails.music21_analysis.beat && (
                    <div>
                      <label className="text-sm font-medium text-blue-600">Beat</label>
                      <p className="text-lg">{selectedNoteDetails.music21_analysis.beat}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Database Matches Section */}
            {selectedNoteDetails.database_matches && (
              <div className="mb-6">
                <h4 className="text-md font-semibold mb-3">数据库精确匹配结果</h4>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Note Set 1 */}
                  <div className="p-4 border rounded-lg">
                    <h5 className="font-medium mb-2 text-green-700">Note Set 1 (combineUnisons=True)</h5>
                    {selectedNoteDetails.database_matches.note_set_1 ? (
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Note ID:</span>
                          <span className="font-mono">{selectedNoteDetails.database_matches.note_set_1.note_id}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Name:</span>
                          <span>{selectedNoteDetails.database_matches.note_set_1.name}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Onset:</span>
                          <span className="font-mono">{selectedNoteDetails.database_matches.note_set_1.onset}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Voice:</span>
                          <span>{selectedNoteDetails.database_matches.note_set_1.voice} ({selectedNoteDetails.database_matches.note_set_1.voice_name})</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Pitch:</span>
                          <span>{selectedNoteDetails.database_matches.note_set_1.pitch}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Measure:</span>
                          <span>{selectedNoteDetails.database_matches.note_set_1.measure}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Duration:</span>
                          <span>{selectedNoteDetails.database_matches.note_set_1.duration}</span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-muted-foreground italic">未找到精确匹配</p>
                    )}
                  </div>

                  {/* Note Set 2 */}
                  <div className="p-4 border rounded-lg">
                    <h5 className="font-medium mb-2 text-purple-700">Note Set 2 (combineUnisons=False)</h5>
                    {selectedNoteDetails.database_matches.note_set_2 ? (
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Note ID:</span>
                          <span className="font-mono">{selectedNoteDetails.database_matches.note_set_2.note_id}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Name:</span>
                          <span>{selectedNoteDetails.database_matches.note_set_2.name}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Onset:</span>
                          <span className="font-mono">{selectedNoteDetails.database_matches.note_set_2.onset}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Voice:</span>
                          <span>{selectedNoteDetails.database_matches.note_set_2.voice} ({selectedNoteDetails.database_matches.note_set_2.voice_name})</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Pitch:</span>
                          <span>{selectedNoteDetails.database_matches.note_set_2.pitch}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Measure:</span>
                          <span>{selectedNoteDetails.database_matches.note_set_2.measure}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Duration:</span>
                          <span>{selectedNoteDetails.database_matches.note_set_2.duration}</span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-muted-foreground italic">未找到精确匹配</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Search Criteria */}
            {selectedNoteDetails.search_criteria && (
              <div className="p-3 bg-gray-50 rounded">
                <h5 className="text-sm font-medium mb-2">搜索条件</h5>
                <div className="flex flex-wrap gap-4 text-sm">
                  <span>Onset: <code>{selectedNoteDetails.search_criteria.onset}</code></span>
                  <span>Voice: <code>{selectedNoteDetails.search_criteria.voice}</code></span>
                  <span>精确匹配: <code>{selectedNoteDetails.search_criteria.exact_match_required ? 'Yes' : 'No'}</code></span>
                </div>
              </div>
            )}

            {/* SVG Info */}
            {selectedNoteDetails.svg_index !== undefined && (
              <div className="mt-4 p-3 bg-muted rounded">
                <p className="text-sm text-muted-foreground">
                  SVG Index: {selectedNoteDetails.svg_index} | 
                  Status: {selectedNoteDetails.music21_analysis ? '✓ Analyzed' : '✗ Analysis Failed'}
                </p>
              </div>
            )}

            {/* Error Information */}
            {selectedNoteDetails.error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded">
                <p className="text-sm text-red-600">
                  Error: {selectedNoteDetails.error}
                </p>
              </div>
            )}
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
          <p>Click on any note in the score to interact with the database</p>
        </div>
      </div>
    </div>
  );
};

export default HomePage;