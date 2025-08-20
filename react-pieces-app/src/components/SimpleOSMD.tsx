import React, { useEffect, useRef, useState } from 'react';
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay';
import { Button } from './ui/button';
import { Piece } from '../types';

interface SimpleOSMDProps {
  piece: Piece | null;
  onNoteClick?: (osmdNoteInfo: any) => void; // 现在只传递OSMD的原始数据
}

const SimpleOSMD: React.FC<SimpleOSMDProps> = ({ piece, onNoteClick }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [osmd, setOsmd] = useState<OpenSheetMusicDisplay | null>(null);
  const [status, setStatus] = useState<string>('Initializing...');
  const [zoom, setZoom] = useState<number>(0.67);

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
        const response = await fetch(`http://localhost:9000/api/pieces/${piece.id}/musicxml`);
        
        if (!response.ok) {
          throw new Error(`API Error: ${response.status}`);
        }
        
        const musicXML = await response.text();
        setStatus('MusicXML loaded, rendering...');
        
        await osmd.load(musicXML);
        // 设置默认缩放值
        (osmd as any).zoom = zoom;
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
        if (!(el as HTMLElement).classList.contains('selected-note')) {
          (el as HTMLElement).style.opacity = '0.7';
        }
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
        // 恢复原始样式
        const element = el as HTMLElement;
        element.style.opacity = '1';
        element.style.fill = '';
        element.style.stroke = '';
        element.style.strokeWidth = '';
        // 对于子元素也恢复样式
        const childElements = el.querySelectorAll('*');
        childElements.forEach(child => {
          const childEl = child as HTMLElement;
          childEl.style.fill = '';
          childEl.style.stroke = '';
          childEl.style.strokeWidth = '';
        });
      });
      
      // 高亮选择的音符为红色
      if (noteInfo.svgElement) {
        noteInfo.svgElement.classList.add('selected-note');
        const element = noteInfo.svgElement as HTMLElement;
        element.style.opacity = '1';
        
        // 设置音符为红色
        element.style.fill = '#ff0000';
        element.style.stroke = '#ff0000';
        element.style.strokeWidth = '1px';
        
        // 对于子元素也设置红色
        const childElements = element.querySelectorAll('*');
        childElements.forEach(child => {
          const childEl = child as HTMLElement;
          childEl.style.fill = '#ff0000';
          childEl.style.stroke = '#ff0000';
        });
      }
      
      // 只传递OSMD的原始数据，让NoteAnalyzer组件处理数据库搜索
      onNoteClick(noteInfo);
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
                    
                    // 获取beat信息 - 考虑拍号的正确计算
                    let beat = 1; // 从1开始的默认值
                    
                    if (staffEntry.sourceStaffEntry?.Timestamp) {
                      // 获取当前小节的拍号信息
                      let timeSignatureNumerator = 4; // 默认4/4拍
                      let timeSignatureDenominator = 4;
                      
                      // 尝试从多个位置获取拍号信息
                      try {
                        if (sourceMeasure?.ActiveTimeSignature) {
                          const ts = sourceMeasure.ActiveTimeSignature as any;
                          timeSignatureNumerator = ts.Numerator || ts.numerator || 4;
                          timeSignatureDenominator = ts.Denominator || ts.denominator || 4;
                        } else if ((sourceMeasure as any)?.timeSignature) {
                          const ts = (sourceMeasure as any).timeSignature;
                          timeSignatureNumerator = ts.Numerator || ts.numerator || 4;
                          timeSignatureDenominator = ts.Denominator || ts.denominator || 4;
                        } else if (osmd.Sheet?.SourceMeasures?.[0]?.ActiveTimeSignature) {
                          const ts = osmd.Sheet.SourceMeasures[0].ActiveTimeSignature as any;
                          timeSignatureNumerator = ts.Numerator || ts.numerator || 4;
                          timeSignatureDenominator = ts.Denominator || ts.denominator || 4;
                        }
                      } catch (tsError) {
                        console.log('Could not get time signature, using 4/4 default:', tsError);
                      }
                      
                      // 计算beat位置：OSMD的RealValue已经是标准化时间戳
                      // 我们需要根据拍号调整计算
                      // RealValue是基于whole note的分数，我们需要转换为基于拍号分母的beat
                      const rawTimestamp = staffEntry.sourceStaffEntry.Timestamp.RealValue;
                      
                      // 计算每拍在whole note中的长度
                      const beatLength = 1.0 / timeSignatureDenominator; // 例如4/4拍中每拍=1/4 whole note
                      
                      // 计算在当前小节中的beat位置（从0开始）
                      const beatInMeasure = rawTimestamp / beatLength;
                      
                      // 转换为从1开始的beat编号
                      beat = beatInMeasure + 1;
                      
                      console.log('Beat calculation debug:', {
                        rawTimestamp,
                        timeSignature: `${timeSignatureNumerator}/${timeSignatureDenominator}`,
                        beatLength,
                        beatInMeasure,
                        finalBeat: beat
                      });
                      
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
                      svgElement: noteSvgElement
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
  };

  // 缩放控制函数
  const handleZoomIn = () => {
    if (!osmd) return;
    const newZoom = zoom * 1.2;
    setZoom(newZoom);
    (osmd as any).zoom = newZoom; // 使用 any 类型来绕过 TypeScript 限制
    osmd.render();
    
    // 重新添加点击事件监听器
    if (onNoteClick) {
      // 延迟执行以确保渲染完成
      setTimeout(() => {
        addClickListeners();
      }, 100);
    }
  };

  const handleZoomOut = () => {
    if (!osmd) return;
    const newZoom = zoom / 1.2;
    setZoom(newZoom);
    (osmd as any).zoom = newZoom; // 使用 any 类型来绕过 TypeScript 限制
    osmd.render();
    
    // 重新添加点击事件监听器
    if (onNoteClick) {
      // 延迟执行以确保渲染完成
      setTimeout(() => {
        addClickListeners();
      }, 100);
    }
  };  return (
    <div className="p-3">
      {/* Status and Zoom Controls in same row */}
      <div className="flex justify-between items-center p-2 bg-muted mb-3 rounded">
        <div>
          <strong>Status:</strong> {status}
        </div>
        
        {/* Zoom Controls */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleZoomOut}
            disabled={!osmd}
            title="Zoom Out"
          >
            −
          </Button>
          
          <span className="min-w-[60px] text-center font-bold text-sm">
            {Math.round(zoom * 100)}%
          </span>
          
          <Button
            variant="outline"
            size="sm"
            onClick={handleZoomIn}
            disabled={!osmd}
            title="Zoom In"
          >
            +
          </Button>
        </div>
      </div>
      
      <div 
        ref={containerRef}
        className="border border-border min-h-[400px] bg-white p-2 rounded overflow-x-hidden overflow-y-auto"
      />
    </div>
  );
};

export default SimpleOSMD;
