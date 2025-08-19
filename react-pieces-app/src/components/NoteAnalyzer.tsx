import React, { useState, useEffect } from 'react';
import { Piece } from '../types';

interface NoteAnalyzerProps {
  piece: Piece | null;
  osmdNoteInfo: any | null; // OSMD提取的音符信息
  onAnalysisComplete?: (analysisResult: any) => void;
}

interface DatabaseNote {
  note_id: number;
  piece_id: number;
  note_set_id: number;
  voice: number;
  voice_name: string | null;
  onset: number;
  duration: number | null;
  offset: number | null;
  measure: number;
  beat: number;
  pitch: number | null;
  name: string | null;
  step: string | null;
  octave: number | null;
  alter: number | null;
  type: string | null;
  staff: number | null;
  tie: string | null;
}

interface AnalysisResult {
  success: boolean;
  database_matches: {
    note_set_1: DatabaseNote | null;
    note_set_2: DatabaseNote | null;
  } | null;
  search_criteria: any;
  osmd_analysis: any;
  error: string | null;
  melodic_ngrams?: MelodicNgramResult | null;
}

interface MelodicNgramSet {
  melodic_ngram_set_id: number;
  ngram_set_slug: string;
  ngram_set_description: string;
  ngrams_number: number;
  interval_kind: string;
  combine_unisons: boolean;
  note_set_slug: string;
  ngrams: MelodicNgram[];
}

interface MelodicNgram {
  ngram_id: number;
  piece_id: number;
  note_id: number;
  voice: number;
  voice_name: string | null;
  onset: number;
  ngram: string;
  ngram_length: number;
}

interface MelodicNgramResult {
  success: boolean;
  results?: {
    [noteId: string]: {
      success: boolean;
      note_info?: DatabaseNote;
      melodic_ngrams: MelodicNgramSet[];
      total_sets: number;
      total_ngrams: number;
      error?: string;
    };
  };
  error?: string;
}

const NoteAnalyzer: React.FC<NoteAnalyzerProps> = ({ 
  piece, 
  osmdNoteInfo, 
  onAnalysisComplete 
}) => {
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 当OSMD音符信息改变时，自动搜索数据库
  useEffect(() => {
    if (piece && osmdNoteInfo) {
      searchInDatabase();
    } else {
      setAnalysisResult(null);
      setError(null);
    }
  }, [piece, osmdNoteInfo]);

  const searchInDatabase = async () => {
    if (!piece || !osmdNoteInfo) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const searchResponse = await fetch(`http://localhost:5000/api/pieces/${piece.id}/notes/search-by-osmd`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          measure: osmdNoteInfo.measureNumber,
          beat: osmdNoteInfo.beat,
          part_id: osmdNoteInfo.partId,
          tolerance: 0.25
        })
      });

      const searchResult = await searchResponse.json();
      
      let melodicNgramsResult: MelodicNgramResult | null = null;
      
      // 如果找到了匹配的音符，获取它们的melodic ngrams
      if (searchResult.success && searchResult.database_matches) {
        const noteIds: number[] = [];
        
        if (searchResult.database_matches.note_set_1?.note_id) {
          noteIds.push(searchResult.database_matches.note_set_1.note_id);
        }
        if (searchResult.database_matches.note_set_2?.note_id) {
          noteIds.push(searchResult.database_matches.note_set_2.note_id);
        }
        
        if (noteIds.length > 0) {
          try {
            const ngramsResponse = await fetch(`http://localhost:5000/api/notes/batch-melodic-ngrams`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                note_ids: noteIds
              })
            });
            
            melodicNgramsResult = await ngramsResponse.json();
          } catch (ngramError) {
            console.warn('Failed to fetch melodic ngrams:', ngramError);
            // 继续执行，不阻断主要功能
          }
        }
      }
      
      const result: AnalysisResult = {
        success: searchResult.success,
        database_matches: searchResult.success ? searchResult.database_matches : null,
        search_criteria: searchResult.success ? searchResult.search_criteria : {
          measure: osmdNoteInfo.measureNumber,
          beat: osmdNoteInfo.beat,
          part_id: osmdNoteInfo.partId,
          voice: osmdNoteInfo.partId,
          position_based_search: true
        },
        osmd_analysis: {
          measure: osmdNoteInfo.measureNumber,
          beat: osmdNoteInfo.beat,
          part_id: osmdNoteInfo.partId,
          part_name: osmdNoteInfo.partName,
          pitch: osmdNoteInfo.pitch,
          duration: osmdNoteInfo.duration,
          extraction_method: 'osmd_api_with_parts'
        },
        error: searchResult.success ? null : searchResult.error,
        melodic_ngrams: melodicNgramsResult
      };

      setAnalysisResult(result);
      
      if (onAnalysisComplete) {
        onAnalysisComplete(result);
      }
      
    } catch (err) {
      const errorMessage = `API调用失败: ${(err as Error).message}`;
      setError(errorMessage);
      
      const errorResult: AnalysisResult = {
        success: false,
        database_matches: null,
        search_criteria: {
          measure: osmdNoteInfo.measureNumber,
          beat: osmdNoteInfo.beat,
          part_id: osmdNoteInfo.partId,
          voice: osmdNoteInfo.partId,
          position_based_search: true
        },
        osmd_analysis: {
          measure: osmdNoteInfo.measureNumber,
          beat: osmdNoteInfo.beat,
          part_id: osmdNoteInfo.partId,
          part_name: osmdNoteInfo.partName,
          pitch: osmdNoteInfo.pitch,
          duration: osmdNoteInfo.duration,
          extraction_method: 'osmd_api_with_parts'
        },
        error: errorMessage,
        melodic_ngrams: null
      };

      setAnalysisResult(errorResult);
      
      if (onAnalysisComplete) {
        onAnalysisComplete(errorResult);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const renderDatabaseNote = (note: DatabaseNote | null, setName: string, colorClass: string) => {
    if (!note) {
      return (
        <div className="p-2 border rounded text-xs">
          <h5 className={`font-medium mb-1 ${colorClass}`}>{setName}</h5>
          <p className="text-muted-foreground text-xs">未找到匹配</p>
        </div>
      );
    }

    return (
      <div className="p-2 border rounded text-xs">
        <h5 className={`font-medium mb-1 ${colorClass}`}>{setName}</h5>
        <div className="space-y-1">
          <div className="flex justify-between">
            <span className="text-muted-foreground">note_id:</span>
            <span className="font-mono text-xs">{note.note_id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">piece_id:</span>
            <span className="font-mono text-xs">{note.piece_id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">note_set_id:</span>
            <span className="font-mono text-xs">{note.note_set_id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">voice:</span>
            <span className="text-xs">{note.voice}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">voice_name:</span>
            <span className="text-xs">{note.voice_name || 'null'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">onset:</span>
            <span className="font-mono text-xs">{note.onset}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">duration:</span>
            <span className="font-mono text-xs">{note.duration || 'null'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">offset:</span>
            <span className="font-mono text-xs">{note.offset || 'null'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">measure:</span>
            <span className="text-xs">{note.measure}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">beat:</span>
            <span className="font-mono text-xs">{note.beat}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">pitch:</span>
            <span className="text-xs">{note.pitch || 'null'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">name:</span>
            <span className="text-xs">{note.name || 'null'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">step:</span>
            <span className="text-xs">{note.step || 'null'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">octave:</span>
            <span className="text-xs">{note.octave || 'null'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">alter:</span>
            <span className="text-xs">{note.alter || 'null'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">type:</span>
            <span className="text-xs">{note.type || 'null'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">staff:</span>
            <span className="text-xs">{note.staff || 'null'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">tie:</span>
            <span className="text-xs">{note.tie || 'null'}</span>
          </div>
        </div>
      </div>
    );
  };

  const renderMelodicNgrams = (melodicNgramsResult: MelodicNgramResult | null) => {
    if (!melodicNgramsResult || !melodicNgramsResult.success || !melodicNgramsResult.results) {
      return null;
    }

    const allNoteIds = Object.keys(melodicNgramsResult.results);
    if (allNoteIds.length === 0) {
      return null;
    }

    return (
      <div className="space-y-3">
        <h4 className="font-semibold text-sm text-indigo-800">旋律N-gram分析</h4>
        
        {allNoteIds.map(noteId => {
          const ngramData = melodicNgramsResult.results![noteId];
          
          if (!ngramData.success || ngramData.melodic_ngrams.length === 0) {
            return (
              <div key={noteId} className="p-2 bg-gray-50 rounded text-xs">
                <p className="text-gray-600">Note ID {noteId}: 未找到melodic ngrams</p>
              </div>
            );
          }

          return (
            <div key={noteId} className="p-3 bg-indigo-50 border border-indigo-200 rounded text-xs">
              <h5 className="font-medium mb-2 text-indigo-800">
                Note ID: {noteId} (共 {ngramData.total_sets} 个集合, {ngramData.total_ngrams} 个ngrams)
              </h5>
              
              <div className="space-y-2">
                {ngramData.melodic_ngrams.map((ngramSet, setIndex) => (
                  <div key={ngramSet.melodic_ngram_set_id} className="p-2 bg-white border rounded">
                    <h6 className="font-medium text-xs text-indigo-700 mb-1">
                      {ngramSet.ngram_set_slug} - {ngramSet.interval_kind} ({ngramSet.ngrams_number}-grams)
                    </h6>
                    <div className="text-xs text-gray-600 mb-1">
                      Set ID: {ngramSet.melodic_ngram_set_id} | 
                      Combine Unisons: {ngramSet.combine_unisons ? 'Yes' : 'No'} |
                      Note Set: {ngramSet.note_set_slug}
                    </div>
                    
                    <div className="space-y-1">
                      {ngramSet.ngrams.map((ngram, ngramIndex) => (
                        <div key={ngram.ngram_id} className="flex justify-between items-center p-1 bg-gray-50 rounded">
                          <div className="flex-1">
                            <span className="font-mono text-xs font-medium text-blue-600">
                              {ngram.ngram}
                            </span>
                            <span className="text-gray-500 text-xs ml-2">
                              (长度: {ngram.ngram_length})
                            </span>
                          </div>
                          <div className="text-xs text-gray-500">
                            ID: {ngram.ngram_id} | Voice: {ngram.voice} | Onset: {ngram.onset}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  if (!osmdNoteInfo) {
    return (
      <div className="text-center text-muted-foreground text-xs mt-8">
        <p>点击乐谱中的音符来查看分析结果</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold mb-3">音符分析</h3>
      
      {/* Loading Indicator */}
      {isLoading && (
        <div className="p-2 bg-yellow-50 rounded text-xs">
          <p className="text-yellow-600">正在搜索数据库...</p>
        </div>
      )}

      {/* OSMD Analysis */}
      {analysisResult?.osmd_analysis && (
        <div className="p-2 bg-blue-50 rounded text-xs">
          <h4 className="font-semibold mb-2 text-blue-800">OSMD 分析</h4>
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-blue-600">小节:</span>
              <span className="font-mono">{analysisResult.osmd_analysis.measure}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-blue-600">拍子:</span>
              <span className="font-mono">{analysisResult.osmd_analysis.beat}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-blue-600">声部ID:</span>
              <span className="font-mono">{analysisResult.osmd_analysis.part_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-blue-600">声部名:</span>
              <span className="text-xs">{analysisResult.osmd_analysis.part_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-blue-600">音高:</span>
              <span className="text-xs">{analysisResult.osmd_analysis.pitch}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-blue-600">时值:</span>
              <span className="text-xs">{analysisResult.osmd_analysis.duration}</span>
            </div>
          </div>
        </div>
      )}

      {/* Database Matches */}
      {analysisResult?.database_matches && (
        <div className="space-y-2">
          <h4 className="font-semibold text-xs">数据库匹配</h4>
          
          {/* Note Set 1 */}
          {renderDatabaseNote(
            analysisResult.database_matches.note_set_1, 
            "Note Set 1 (combine_unisons=True)", 
            "text-green-700"
          )}

          {/* Note Set 2 */}
          {renderDatabaseNote(
            analysisResult.database_matches.note_set_2, 
            "Note Set 2 (combine_unisons=False)", 
            "text-purple-700"
          )}
        </div>
      )}

      {/* Search Criteria */}
      {analysisResult?.search_criteria && (
        <div className="p-2 bg-gray-50 rounded text-xs">
          <h5 className="font-medium mb-1">搜索条件</h5>
          <div className="space-y-1">
            <div>小节: <code className="text-xs">{analysisResult.search_criteria.measure}</code></div>
            <div>拍子: <code className="text-xs">{analysisResult.search_criteria.beat}</code></div>
            <div>声部: <code className="text-xs">{analysisResult.search_criteria.part_id || analysisResult.search_criteria.voice}</code></div>
            <div>搜索类型: <code className="text-xs">基于位置匹配</code></div>
          </div>
        </div>
      )}

      {/* Melodic N-grams */}
      {analysisResult?.melodic_ngrams && renderMelodicNgrams(analysisResult.melodic_ngrams)}

      {/* Error Information */}
      {(error || analysisResult?.error) && (
        <div className="p-2 bg-red-50 border border-red-200 rounded text-xs">
          <p className="text-red-600">错误: {error || analysisResult?.error}</p>
        </div>
      )}
    </div>
  );
};

export default NoteAnalyzer;
