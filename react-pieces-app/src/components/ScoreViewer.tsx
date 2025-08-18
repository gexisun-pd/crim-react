import React, { useEffect, useRef, useState } from 'react';
import { Piece } from '../types';

// 声明 Verovio 全局变量
declare global {
  interface Window {
    verovio: {
      toolkit: new () => VerovioToolkit;
    };
  }
}

interface ScoreViewerProps {
  piece: Piece | null;
  onNoteClick?: (noteDetails: any) => void;
  className?: string;
}

interface SvgMapping {
  [key: string]: {
    note_id: number;
    onset: number;
    voice_id: number;
    pitch_name: string;
    midi_note?: number;
    octave?: number;
    measure?: number;
    beat?: number;
    duration: number;
    database_onset: number;
    database_voice: number;
    database_name: string;
    match_distance: number;
  };
}

interface VerovioToolkit {
  loadData(data: string): boolean;
  renderToSVG(pageNumber?: number, options?: any): string;
  setOptions(options: any): void;
  getElementsAtTime(time: number): string[];
  getTimeForElement(elementId: string): number;
}

const ScoreViewer: React.FC<ScoreViewerProps> = ({ 
  piece, 
  onNoteClick, 
  className = '' 
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [verovio, setVerovio] = useState<VerovioToolkit | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [svgMapping, setSvgMapping] = useState<SvgMapping>({});
  const [isLoadingMapping, setIsLoadingMapping] = useState(false);
  const [svgContent, setSvgContent] = useState<string>('');

  // 初始化 Verovio
  useEffect(() => {
    const initializeVerovio = () => {
      // 检查 Verovio 是否已加载
      if (window.verovio && window.verovio.toolkit) {
        try {
          const vrvToolkit = new window.verovio.toolkit();
          
          // 设置 Verovio 选项
          vrvToolkit.setOptions({
            adjustPageHeight: true,
            pageHeight: 2970,
            pageWidth: 2100,
            scale: 40,
            font: 'Leipzig',
            header: 'none',
            footer: 'none',
            breaks: 'auto'
          });
          
          setVerovio(vrvToolkit);
          console.log('Verovio initialized successfully');
        } catch (err) {
          console.error('Failed to initialize Verovio:', err);
          setError('Failed to initialize music notation engine');
        }
      } else {
        // 如果 Verovio 还没加载，等待一下再试
        setTimeout(initializeVerovio, 100);
      }
    };

    initializeVerovio();
  }, []);

  // 加载并渲染乐谱
  useEffect(() => {
    if (!verovio || !piece) {
      setSvgContent('');
      return;
    }

    const loadScore = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // 从 Flask API 获取 MusicXML 内容
        const response = await fetch(`http://localhost:5000/api/pieces/${piece.id}/musicxml`);
        
        if (!response.ok) {
          throw new Error(`Failed to load score: ${response.status}`);
        }
        
        const musicXML = await response.text();
        
        // 加载准确的 SVG 映射 using music21
        setIsLoadingMapping(true);
        try {
          const mappingResponse = await fetch(`http://localhost:5000/api/pieces/${piece.id}/svg-mapping?note_set_id=1`);
          if (mappingResponse.ok) {
            const mappingData = await mappingResponse.json();
            if (mappingData.success) {
              setSvgMapping(mappingData.mapping);
              console.log(`Loaded accurate mapping for ${Object.keys(mappingData.mapping).length} notes`);
            } else {
              console.warn('Failed to load SVG mapping:', mappingData.error);
            }
          } else {
            console.warn('Mapping API unavailable, using fallback method');
          }
        } catch (mappingError) {
          console.warn('Error loading mapping:', mappingError);
        } finally {
          setIsLoadingMapping(false);
        }
        
        // 使用 Verovio 加载 MusicXML
        const success = verovio.loadData(musicXML);
        if (!success) {
          throw new Error('Failed to parse MusicXML data');
        }
        
        // 渲染为 SVG
        const svg = verovio.renderToSVG(1);
        setSvgContent(svg);
        
        console.log('Score loaded successfully for piece:', piece.title);
        
      } catch (err) {
        console.error('Error loading score:', err);
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
      } finally {
        setIsLoading(false);
      }
    };

    loadScore();
  }, [verovio, piece]);

  // 处理 SVG 点击事件
  useEffect(() => {
    if (!containerRef.current || !svgContent || !onNoteClick) return;

    const handleSvgClick = async (event: MouseEvent) => {
      const target = event.target as Element;
      
      // 查找被点击的音符元素 - Verovio 通常使用 'note' 类
      const noteElement = target.closest('.note');
      
      if (noteElement) {
        try {
          console.log('Clicked note element:', noteElement);
          
          // 获取SVG中所有音符元素来确定索引
          const svgElement = containerRef.current?.querySelector('svg');
          if (svgElement) {
            const allNotes = Array.from(svgElement.querySelectorAll('.note'));
            const noteIndex = allNotes.indexOf(noteElement);
            
            console.log(`Note clicked: SVG index ${noteIndex}`);
            
            // 先尝试使用准确的映射
            const mappedNote = svgMapping[noteIndex.toString()];
            
            if (mappedNote) {
              console.log('Found mapped note:', mappedNote);
              
              // 获取详细的数据库信息
              const response = await fetch(`http://localhost:5000/api/notes/${mappedNote.note_id}/details`);
              if (response.ok) {
                const data = await response.json();
                if (data.success && onNoteClick) {
                  // 添加music21映射信息到响应中
                  const enrichedData = {
                    ...data.data,
                    music21_onset: mappedNote.onset,
                    music21_pitch_name: mappedNote.pitch_name,
                    music21_voice_id: mappedNote.voice_id,
                    music21_duration: mappedNote.duration,
                    music21_measure: mappedNote.measure,
                    music21_beat: mappedNote.beat,
                    svg_index: noteIndex,
                    match_distance: mappedNote.match_distance
                  };
                  
                  // 高亮点击的音符
                  highlightNote(noteElement);
                  
                  onNoteClick(enrichedData);
                  return;
                }
              }
            }
            
            console.log('No mapping found, using music21 analysis API...');
            
            // 备选方案：使用实时music21分析
            if (piece) {
              const response = await fetch(`http://localhost:5000/api/pieces/${piece.id}/analyze-with-music21`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({ svg_index: noteIndex })
              });
              
              if (response.ok) {
                const data = await response.json();
                if (data.success && onNoteClick) {
                  // 高亮点击的音符
                  highlightNote(noteElement);
                  onNoteClick(data.data);
                  return;
                }
              }
            }
            
            // 最后的备选方案：显示基本信息
            console.warn('All mapping methods failed');
            onNoteClick({
              message: 'Note clicked but could not retrieve database information',
              svg_element_id: noteElement.getAttribute('id'),
              svg_element_class: noteElement.getAttribute('class'),
              svg_index: noteIndex
            });
          }
          
        } catch (error) {
          console.error('Error handling note click:', error);
          onNoteClick({
            message: 'Error processing note click',
            error: error instanceof Error ? error.message : 'Unknown error'
          });
        }
      }
    };

    const svgElement = containerRef.current.querySelector('svg');
    if (svgElement) {
      svgElement.addEventListener('click', handleSvgClick);
      
      // 添加鼠标悬停效果
      const noteElements = svgElement.querySelectorAll('.note');
      noteElements.forEach(noteEl => {
        (noteEl as HTMLElement).style.cursor = 'pointer';
        
        noteEl.addEventListener('mouseenter', () => {
          (noteEl as HTMLElement).style.opacity = '0.8';
        });
        
        noteEl.addEventListener('mouseleave', () => {
          if (!noteEl.classList.contains('note-selected')) {
            (noteEl as HTMLElement).style.opacity = '1';
          }
        });
      });
      
      return () => {
        svgElement.removeEventListener('click', handleSvgClick);
      };
    }
  }, [svgContent, onNoteClick, piece]);
  
  // 提取音符位置信息的辅助函数
  const extractNotePosition = (noteElement: Element): { voice: number; onset: number } | null => {
    try {
      // 策略1: 尝试从父元素中提取measure和layer信息
      let currentElement = noteElement as Element;
      let measureNumber = 1;
      let layerNumber = 1;
      
      // 向上遍历寻找measure信息
      while (currentElement && currentElement.tagName !== 'svg') {
        const elementClass = currentElement.getAttribute('class') || '';
        const elementId = currentElement.getAttribute('id') || '';
        
        // 查找measure信息
        if (elementClass.includes('measure') || elementId.includes('measure')) {
          const measureMatch = elementId.match(/measure-(\d+)/);
          if (measureMatch) {
            measureNumber = parseInt(measureMatch[1]);
          }
        }
        
        // 查找layer/voice信息
        if (elementClass.includes('layer') || elementId.includes('layer')) {
          const layerMatch = elementId.match(/layer-(\d+)/);
          if (layerMatch) {
            layerNumber = parseInt(layerMatch[1]);
          }
        }
        
        currentElement = currentElement.parentElement as Element;
      }
      
      // 策略2: 根据在SVG中的位置估算onset
      // 这是一个简化的方法，实际应用中可能需要更复杂的计算
      const svgElement = containerRef.current?.querySelector('svg');
      if (svgElement) {
        const allNotes = Array.from(svgElement.querySelectorAll('.note'));
        const noteIndex = allNotes.indexOf(noteElement);
        
        // 简单估算：每个音符大约0.5拍
        const estimatedOnset = noteIndex * 0.5;
        
        return {
          voice: layerNumber,
          onset: estimatedOnset
        };
      }
      
      return null;
      
    } catch (error) {
      console.error('Error extracting note position:', error);
      return null;
    }
  };
  
  // 高亮音符的辅助函数
  const highlightNote = (noteElement: Element) => {
    // 清除之前的高亮
    const svgElement = containerRef.current?.querySelector('svg');
    if (svgElement) {
      svgElement.querySelectorAll('.note-selected').forEach(el => {
        el.classList.remove('note-selected');
        (el as HTMLElement).style.opacity = '1';
        (el as HTMLElement).style.fill = '';
      });
    }
    
    // 添加新的高亮
    noteElement.classList.add('note-selected');
    (noteElement as HTMLElement).style.opacity = '1';
    (noteElement as HTMLElement).style.fill = '#ff6b6b';
  };

  if (isLoading) {
    return (
      <div className={`flex items-center justify-center min-h-[400px] ${className}`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-2 text-sm text-muted-foreground">Loading score...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center min-h-[400px] ${className}`}>
        <div className="text-center">
          <p className="text-red-600 mb-2">Error loading score</p>
          <p className="text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  if (!piece) {
    return (
      <div className={`flex items-center justify-center min-h-[400px] border-2 border-dashed border-muted rounded-lg ${className}`}>
        <p className="text-muted-foreground">Select a piece to view the score</p>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border shadow-sm overflow-auto ${className}`}>
      <div className="p-4 border-b bg-muted/50">
        <h3 className="font-semibold text-lg">{piece.title}</h3>
        <p className="text-sm text-muted-foreground">
          {piece.composer} • {piece.filename}
        </p>
      </div>
      
      <div 
        ref={containerRef}
        className="p-6 overflow-x-auto"
        dangerouslySetInnerHTML={{ __html: svgContent }}
      />
    </div>
  );
};

export default ScoreViewer;
