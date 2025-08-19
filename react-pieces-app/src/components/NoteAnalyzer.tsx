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
        error: searchResult.success ? null : searchResult.error
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
        error: errorMessage
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
