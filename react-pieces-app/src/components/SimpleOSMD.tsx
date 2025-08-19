import React, { useEffect, useRef, useState } from 'react';
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay';
import { Piece } from '../types';

interface SimpleOSMDProps {
  piece: Piece | null;
  onNoteClick?: (noteDetails: any) => void;
}

const SimpleOSMD: React.FC<SimpleOSMDProps> = ({ piece, onNoteClick }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [osmd, setOsmd] = useState<OpenSheetMusicDisplay | null>(null);
  const [status, setStatus] = useState<string>('Initializing...');

  useEffect(() => {
    const initAndLoad = async () => {
      try {
        if (!containerRef.current) {
          setStatus('Container not ready');
          return;
        }

        setStatus('Creating OSMD instance...');
        console.log('Container:', containerRef.current);

        const osmdInstance = new OpenSheetMusicDisplay(containerRef.current, {
          autoResize: true,
          backend: 'svg',
          drawTitle: true,
          drawComposer: true,
          drawMeasureNumbers: true,
          pageFormat: 'Letter'
        });

        setOsmd(osmdInstance);
        setStatus('OSMD created successfully');
        
      } catch (error) {
        console.error('OSMD Error:', error);
        setStatus('Error: ' + (error as Error).message);
      }
    };

    // 延迟执行以确保容器已挂载
    const timer = setTimeout(initAndLoad, 100);
    return () => clearTimeout(timer);
  }, []);

  // 当 piece 改变时加载新的乐谱
  useEffect(() => {
    if (!osmd || !piece) {
      if (piece) {
        setStatus('OSMD not ready yet...');
      } else {
        setStatus('No piece selected');
      }
      return;
    }

    const loadScore = async () => {
      try {
        setStatus('Loading MusicXML from API...');
        const response = await fetch(`http://localhost:5000/api/pieces/${piece.id}/musicxml`);
        
        if (!response.ok) {
          throw new Error(`API Error: ${response.status}`);
        }
        
        const musicXML = await response.text();
        setStatus('MusicXML loaded, rendering...');
        
        await osmd.load(musicXML);
        await osmd.render();
        setStatus('Score rendered successfully!');
        
        // 添加点击事件监听器
        if (onNoteClick) {
          addClickListeners();
        }
        
      } catch (error) {
        console.error('Loading Error:', error);
        setStatus('Error loading score: ' + (error as Error).message);
      }
    };

    loadScore();
  }, [osmd, piece]);

  const addClickListeners = () => {
    const svg = containerRef.current?.querySelector('svg');
    if (!svg) return;
    
    // 移除现有监听器
    svg.removeEventListener('click', handleNoteClick);
    
    // 添加新监听器
    svg.addEventListener('click', handleNoteClick);
    
    // 样式化可点击元素
    const noteElements = svg.querySelectorAll('[id*="note"], [id*="vf-"], [class*="note"]');
    noteElements.forEach(el => {
      (el as HTMLElement).style.cursor = 'pointer';
      el.addEventListener('mouseenter', () => {
        (el as HTMLElement).style.opacity = '0.7';
      });
      el.addEventListener('mouseleave', () => {
        if (!(el as HTMLElement).classList.contains('selected-note')) {
          (el as HTMLElement).style.opacity = '1';
        }
      });
    });
  };

  const handleNoteClick = (event: MouseEvent) => {
    const target = event.target as SVGElement;
    
    // 使用OSMD的正确API查找被点击的音符
    const noteInfo = findClickedNoteWithOSMDAPI(target);
    
    if (noteInfo && onNoteClick) {
      console.log('Clicked note with OSMD API:', noteInfo);
      
      // 清除之前的选择
      document.querySelectorAll('.selected-note').forEach(el => {
        el.classList.remove('selected-note');
        (el as HTMLElement).style.opacity = '1';
      });
      
      // 高亮选择的音符
      if (noteInfo.svgElement) {
        noteInfo.svgElement.classList.add('selected-note');
        (noteInfo.svgElement as HTMLElement).style.opacity = '1';
      }
      
      const noteDetails = {
        osmd_analysis: {
          measure: noteInfo.measureNumber,
          beat: noteInfo.beat,
          voice_id: noteInfo.partId, // Part ID (真正的声部编号)
          voice_name: noteInfo.partName, // Part Name (真正的声部名称)
          part_id: noteInfo.partId, // 新增：明确的 part 信息
          part_name: noteInfo.partName,
          voice_index: noteInfo.voiceIndex, // Voice 是 Part 内的子层
          pitch: noteInfo.pitch,
          duration: noteInfo.duration,
          extraction_method: 'osmd_api_with_parts'
        },
        svg_analysis: {
          measure: noteInfo.measureNumber,
          beat: noteInfo.beat,
          voice: noteInfo.partName, // 保持兼容性
          voice_id: noteInfo.partId,
          voice_name: noteInfo.partName,
          part_id: noteInfo.partId,
          part_name: noteInfo.partName,
          svg_id: noteInfo.svgElement?.id || 'unknown'
        },
        search_criteria: {
          measure: noteInfo.measureNumber,
          beat: noteInfo.beat,
          voice: noteInfo.partId, // 使用 Part ID 进行搜索
          voice_name: noteInfo.partName,
          part_id: noteInfo.partId,
          part_name: noteInfo.partName,
          position_based_search: true
        },
        raw_osmd_data: noteInfo
      };
      
      onNoteClick(noteDetails);
    }
  };

  // 使用OSMD的正确API查找被点击的音符
  const findClickedNoteWithOSMDAPI = (target: SVGElement) => {
    if (!osmd || !osmd.Sheet) {
      return null;
    }

    try {
      // 使用 any 类型来绕过 TypeScript 限制，因为 OSMD 的内部结构可能不完全暴露
      const osmdAny = osmd as any;
      
      // 检查是否有图形表示
      const graphic = osmdAny.GraphicSheet || osmdAny.graphic;
      if (!graphic) {
        return null;
      }
      
      // 尝试访问 measureList 或 MeasureList
      const measureList = graphic.measureList || graphic.MeasureList || graphic.MusicPages?.[0]?.MusicSystems?.[0]?.StaffLines?.[0]?.Measures;
      
      if (!measureList) {
        console.log('No measure list found in graphic sheet');
        return null;
      }

      // 首先获取所有 Parts 信息用于调试
      console.log('OSMD Sheet structure:', {
        instruments: osmd.Sheet?.Instruments?.length || 0,
        sourceMeasures: osmd.Sheet?.SourceMeasures?.length || 0,
        parts: osmd.Sheet?.Instruments?.map((inst, idx) => ({
          index: idx,
          name: inst.Name,
          id: (inst as any).IdString || (inst as any).id,
          voices: (inst as any).Voices?.length || 0
        }))
      });
      
      // 遍历所有小节
      for (let measureIndex = 0; measureIndex < measureList.length; measureIndex++) {
        const measuresInSystem = measureList[measureIndex];
        
        // 如果是单个measure而不是数组
        const measures = Array.isArray(measuresInSystem) ? measuresInSystem : [measuresInSystem];
        
        for (let staffIndex = 0; staffIndex < measures.length; staffIndex++) {
          const measure = measures[staffIndex];
          
          if (!measure || !measure.staffEntries) {
            continue;
          }
          
          // 检查每个staff entry
          for (const staffEntry of measure.staffEntries) {
            if (!staffEntry.graphicalVoiceEntries) {
              continue;
            }
            
            // 检查每个voice entry
            for (let voiceIndex = 0; voiceIndex < staffEntry.graphicalVoiceEntries.length; voiceIndex++) {
              const graphicalVoiceEntry = staffEntry.graphicalVoiceEntries[voiceIndex];
              
              if (!graphicalVoiceEntry.notes) {
                continue;
              }
              
              // 检查每个音符
              for (const graphicalNote of graphicalVoiceEntry.notes) {
                try {
                  let noteSvgElement = null;
                  
                  // 尝试多种方法获取SVG元素
                  if (typeof graphicalNote.getSVGGElement === 'function') {
                    noteSvgElement = graphicalNote.getSVGGElement();
                  } else if (graphicalNote.SVGElement) {
                    noteSvgElement = graphicalNote.SVGElement;
                  } else if (graphicalNote.svgElement) {
                    noteSvgElement = graphicalNote.svgElement;
                  }
                  
                  // 检查点击的元素是否是这个音符或其子元素
                  if (noteSvgElement && (noteSvgElement === target || noteSvgElement.contains(target))) {
                    // 获取measure number
                    const sourceMeasure = osmd.Sheet?.SourceMeasures?.[measureIndex];
                    const measureNumber = sourceMeasure ? sourceMeasure.MeasureNumber : measureIndex + 1;
                    
                    // 获取beat信息 - 尝试多种方法
                    let beat = 1; // 从1开始的默认值
                    
                    if (staffEntry.sourceStaffEntry?.Timestamp) {
                      // OSMD的时间戳通常从0开始，我们需要转换为从1开始的beat
                      const rawBeat = staffEntry.sourceStaffEntry.Timestamp.RealValue * 4;
                      beat = rawBeat + 1; // 转换为从1开始
                    } else if (staffEntry.relativePosition) {
                      // 如果有相对位置信息，也进行类似转换
                      const rawBeat = staffEntry.relativePosition.x || 0;
                      beat = rawBeat + 1;
                    } else {
                      // 如果没有时间戳信息，基于voice index估算
                      beat = voiceIndex + 1;
                    }

                    // 获取Part信息 - 这是关键！
                    let partId = staffIndex + 1; // 默认值
                    let partName = `Part ${partId}`;
                    
                    // 方法1: 从 Instruments 获取 Part 信息
                    if (osmd.Sheet?.Instruments && osmd.Sheet.Instruments[staffIndex]) {
                      const instrument = osmd.Sheet.Instruments[staffIndex];
                      partName = instrument.Name || partName;
                      
                      // 尝试获取 Part ID
                      if ((instrument as any).IdString) {
                        partId = parseInt((instrument as any).IdString.replace(/\D/g, '')) || partId;
                      } else if ((instrument as any).id) {
                        partId = parseInt((instrument as any).id.toString().replace(/\D/g, '')) || partId;
                      }
                    }
                    
                    // 方法2: 从 graphicalVoiceEntry 的父级结构获取
                    const sourceVoiceEntry = graphicalVoiceEntry.parentVoiceEntry;
                    if (sourceVoiceEntry?.ParentVoice?.Parent) {
                      const parentInstrument = sourceVoiceEntry.ParentVoice.Parent;
                      if (parentInstrument.Name) {
                        partName = parentInstrument.Name;
                      }
                      if ((parentInstrument as any).IdString) {
                        const extractedId = parseInt((parentInstrument as any).IdString.replace(/\D/g, ''));
                        if (!isNaN(extractedId)) {
                          partId = extractedId;
                        }
                      }
                    }
                    
                    // 方法3: 从 SourceMeasure 获取 Part 信息
                    if (sourceMeasure && (sourceMeasure as any).parentSourceMeasure?.parentPart) {
                      const parentPart = (sourceMeasure as any).parentSourceMeasure.parentPart;
                      if (parentPart.Name) {
                        partName = parentPart.Name;
                      }
                      if (parentPart.IdString) {
                        const extractedId = parseInt(parentPart.IdString.replace(/\D/g, ''));
                        if (!isNaN(extractedId)) {
                          partId = extractedId;
                        }
                      }
                    }
                    
                    // 确保partId是数字
                    if (typeof partId !== 'number' || isNaN(partId)) {
                      partId = staffIndex + 1;
                    }
                    
                    // 获取音符详细信息
                    const sourceNote = graphicalNote.sourceNote;
                    let pitch = 'unknown';
                    let duration = 'unknown';
                    
                    if (sourceNote) {
                      if (sourceNote.Pitch?.ToString) {
                        pitch = sourceNote.Pitch.ToString();
                      }
                      if (sourceNote.Length) {
                        duration = sourceNote.Length.toString();
                      }
                    }
                    
                    // 调试信息
                    console.log('Part debug info:', {
                      measureIndex,
                      staffIndex,
                      voiceIndex,
                      partId,
                      partName,
                      instrumentsCount: osmd.Sheet?.Instruments?.length || 0,
                      instrumentAtIndex: osmd.Sheet?.Instruments?.[staffIndex] ? 'exists' : 'null',
                      instrumentName: osmd.Sheet?.Instruments?.[staffIndex]?.Name || 'unknown'
                    });
                    
                    return {
                      measureNumber: measureNumber,
                      measureIndex: measureIndex,
                      beat: Math.round(beat * 100) / 100, // 保留两位小数，已转换为从1开始
                      partId: partId, // Part ID (这才是真正的 voice_id)
                      partName: partName, // Part Name (这才是真正的 voice_name)
                      staffIndex: staffIndex,
                      voiceIndex: voiceIndex, // Voice 是 Part 内的子层
                      pitch: pitch,
                      duration: duration,
                      sourceNote: sourceNote,
                      graphicalNote: graphicalNote,
                      staffEntry: staffEntry,
                      svgElement: noteSvgElement,
                      note: 'Beat值已从OSMD的0-based系统转换为1-based系统，partId为声部编号，partName为声部名称'
                    };
                  }
                } catch (noteError) {
                  // 继续检查下一个音符
                  console.log('Error checking note:', noteError);
                  continue;
                }
              }
            }
          }
        }
      }
      
      return null;
    } catch (error) {
      console.error('Error finding note with OSMD API:', error);
      return null;
    }
  };  return (
    <div style={{ padding: '20px' }}>
      <div style={{ 
        padding: '10px', 
        backgroundColor: '#f8f9fa', 
        marginBottom: '10px',
        borderRadius: '4px'
      }}>
        <strong>Status:</strong> {status}
        {piece && (
          <div style={{ marginTop: '5px', fontSize: '14px', color: '#666' }}>
            Loading: {piece.title} by {piece.composer}
          </div>
        )}
        <div style={{ marginTop: '5px', fontSize: '12px', color: '#888' }}>
          使用 OSMD 原生 API 提取音符信息。Beat 从1开始，使用 Part ID/Name 作为声部信息（而非 Voice）
        </div>
      </div>
      
      <div 
        ref={containerRef}
        style={{ 
          border: '1px solid #ddd', 
          minHeight: '400px', 
          backgroundColor: 'white',
          padding: '10px'
        }}
      />
    </div>
  );
};

export default SimpleOSMD;
