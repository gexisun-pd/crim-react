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
        
        console.log('OSMD Sheet:', osmd.Sheet);
        
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
    const target = event.target as Element;
    
    // 查找被点击的音符元素
    const noteElement = target.closest('[id*="note"], [id*="vf-"], [class*="note"]');
    
    if (noteElement && onNoteClick) {
      console.log('Clicked note element:', noteElement);
      
      // 清除之前的选择
      document.querySelectorAll('.selected-note').forEach(el => {
        el.classList.remove('selected-note');
        (el as HTMLElement).style.opacity = '1';
        (el as HTMLElement).style.fill = '';
      });
      
      // 高亮选择的音符
      noteElement.classList.add('selected-note');
      (noteElement as HTMLElement).style.opacity = '1';
      (noteElement as HTMLElement).style.fill = '#ff6b6b';
      
      // 提取基本信息
      const elementId = noteElement.getAttribute('id') || '';
      const elementClass = noteElement.getAttribute('class') || '';
      
      // 简单的位置估算
      const position = estimateNotePosition(noteElement);
      
      const noteDetails = {
        element_id: elementId,
        element_class: elementClass,
        estimated_position: position,
        osmd_analysis: {
          measure: position.measure,
          beat: position.beat,
          voice: position.voice,
          extraction_method: 'simple_estimation'
        },
        message: 'Note clicked - using simple position estimation'
      };
      
      console.log('Note details:', noteDetails);
      onNoteClick(noteDetails);
    }
  };

  const estimateNotePosition = (noteElement: Element) => {
    // 简单的位置估算逻辑
    const svg = containerRef.current?.querySelector('svg');
    if (!svg) {
      return { measure: 1, beat: 1, voice: 1 };
    }
    
    const allElements = Array.from(svg.querySelectorAll('[id*="note"], [id*="vf-"]'));
    const elementIndex = allElements.indexOf(noteElement);
    
    if (elementIndex >= 0) {
      // 粗略估算：假设每小节4个音符
      const estimatedMeasure = Math.floor(elementIndex / 4) + 1;
      const estimatedBeat = (elementIndex % 4) + 1;
      
      return {
        measure: estimatedMeasure,
        beat: estimatedBeat,
        voice: 1,
        element_index: elementIndex
      };
    }
    
    return { measure: 1, beat: 1, voice: 1 };
  };

  return (
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
