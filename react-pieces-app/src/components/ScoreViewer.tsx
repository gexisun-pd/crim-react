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
  onNoteClick?: (noteId: string, element: Element) => void;
  className?: string;
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
      setLoading(true);
      setError(null);
      
      try {
        // 从 Flask API 获取 MusicXML 内容
        const response = await fetch(`http://localhost:5000/api/pieces/${piece.id}/musicxml`);
        
        if (!response.ok) {
          throw new Error(`Failed to load score: ${response.status}`);
        }
        
        const musicXML = await response.text();
        
        // 使用 Verovio 加载 MusicXML
        const success = verovio.loadData(musicXML);
        if (!success) {
          throw new Error('Failed to parse MusicXML data');
        }
        
        // 渲染为 SVG
        const svg = verovio.renderToSVG(1);
        setSvgContent(svg);
        
      } catch (err) {
        console.error('Error loading score:', err);
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    loadScore();
  }, [verovio, piece]);

  // 处理 SVG 点击事件
  useEffect(() => {
    if (!containerRef.current || !svgContent || !onNoteClick) return;

    const handleSvgClick = (event: MouseEvent) => {
      const target = event.target as Element;
      
      // 查找被点击的音符元素
      const noteElement = target.closest('.note, .chord');
      if (noteElement) {
        const noteId = noteElement.id;
        if (noteId) {
          onNoteClick(noteId, noteElement);
        }
      }
    };

    const svgElement = containerRef.current.querySelector('svg');
    if (svgElement) {
      svgElement.addEventListener('click', handleSvgClick);
      
      // 添加鼠标悬停效果
      svgElement.style.cursor = 'pointer';
      
      return () => {
        svgElement.removeEventListener('click', handleSvgClick);
      };
    }
  }, [svgContent, onNoteClick]);

  if (loading) {
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
