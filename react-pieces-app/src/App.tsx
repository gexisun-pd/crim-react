import React, { useState } from 'react';
import PieceViewer from './pages/PieceViewer';
import OSMDTest from './components/OSMDTest';
import './App.css';

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<'main' | 'osmd'>('main');

  return (
    <div className="App">
      <div style={{ padding: '10px', backgroundColor: '#f0f0f0', borderBottom: '1px solid #ddd' }}>
        <button 
          onClick={() => setCurrentPage('main')}
          style={{ 
            padding: '8px 16px', 
            backgroundColor: currentPage === 'main' ? '#28a745' : '#007bff', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px',
            cursor: 'pointer',
            marginRight: '10px'
          }}
        >
          Piece Viewer (Main App)
        </button>
        <button 
          onClick={() => setCurrentPage('osmd')}
          style={{ 
            padding: '8px 16px', 
            backgroundColor: currentPage === 'osmd' ? '#28a745' : '#007bff', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          OSMD Test Component
        </button>
      </div>
      
      {currentPage === 'main' && <PieceViewer />}
      {currentPage === 'osmd' && <OSMDTest />}
    </div>
  );
};

export default App;