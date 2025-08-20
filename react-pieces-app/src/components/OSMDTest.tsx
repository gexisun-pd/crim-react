import React, { useEffect, useRef, useState } from 'react';
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay';
import { getApiBaseUrl } from '../config/api';
import { apiService } from '../services/api';

const OSMDTest: React.FC = () => {
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
        setStatus('OSMD created, loading MusicXML...');
        
        // 使用简单的测试 MusicXML
        const testMusicXML = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work>
    <work-title>Test Score</work-title>
  </work>
  <identification>
    <creator type="composer">Test Composer</creator>
  </identification>
  <part-list>
    <score-part id="P1">
      <part-name>Test Part</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key>
          <fifths>0</fifths>
        </key>
        <time>
          <beats>4</beats>
          <beat-type>4</beat-type>
        </time>
        <clef>
          <sign>G</sign>
          <line>2</line>
        </clef>
      </attributes>
      <note>
        <pitch>
          <step>C</step>
          <octave>4</octave>
        </pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch>
          <step>D</step>
          <octave>4</octave>
        </pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch>
          <step>E</step>
          <octave>4</octave>
        </pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch>
          <step>F</step>
          <octave>4</octave>
        </pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>`;

        await osmdInstance.load(testMusicXML);
        setStatus('MusicXML loaded, rendering...');
        
        await osmdInstance.render();
        setStatus('Score rendered successfully!');
        
        console.log('OSMD Sheet:', osmdInstance.Sheet);
        
      } catch (error) {
        console.error('OSMD Test Error:', error);
        setStatus('Error: ' + (error as Error).message);
      }
    };

    // 延迟执行以确保容器已挂载
    const timer = setTimeout(initAndLoad, 100);
    return () => clearTimeout(timer);
  }, []);

  const loadRealMusicXML = async () => {
    if (!osmd) {
      setStatus('OSMD not initialized');
      return;
    }

    try {
      setStatus('Loading real MusicXML from API...');
      const musicXML = await apiService.getPieceMusicXML(1);
      
      if (!musicXML) {
        throw new Error('Failed to load MusicXML');
      }
      
      setStatus('Real MusicXML loaded, rendering...');
      
      await osmd.load(musicXML);
      await osmd.render();
      setStatus('Real score rendered successfully!');
      
    } catch (error) {
      console.error('Real MusicXML Error:', error);
      setStatus('Error loading real MusicXML: ' + (error as Error).message);
    }
  };

  return (
    <div className="h-full bg-background p-4">
      <div className="max-w-full mx-auto h-full">
        <div className="mb-4">
          <h1 className="text-2xl font-bold text-foreground mb-2">OSMD Test Component</h1>
          <p className="text-muted-foreground">Status: {status}</p>
          <button 
            onClick={loadRealMusicXML}
            disabled={!osmd}
            className="mt-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Load Real MusicXML
          </button>
        </div>
        
        <div 
          ref={containerRef}
          className="border rounded-lg bg-white p-4 h-[calc(100vh-200px)] overflow-auto"
        />
      </div>
    </div>
  );
};

export default OSMDTest;
