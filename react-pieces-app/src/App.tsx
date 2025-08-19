import React, { useState } from 'react';
import HomePage from './pages/HomePage';
import TestPage from './pages/TestPage';
import OSMDTest from './components/OSMDTest';
import './App.css';

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<'home' | 'test' | 'osmd'>('test');

  return (
    <div className="App">
      <div style={{ padding: '10px', backgroundColor: '#f0f0f0', borderBottom: '1px solid #ddd' }}>
        <button 
          onClick={() => setCurrentPage('home')}
          style={{ 
            padding: '8px 16px', 
            backgroundColor: currentPage === 'home' ? '#28a745' : '#007bff', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px',
            cursor: 'pointer',
            marginRight: '10px'
          }}
        >
          Original HomePage
        </button>
        <button 
          onClick={() => setCurrentPage('test')}
          style={{ 
            padding: '8px 16px', 
            backgroundColor: currentPage === 'test' ? '#28a745' : '#007bff', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px',
            cursor: 'pointer',
            marginRight: '10px'
          }}
        >
          Test Page (SimpleOSMD)
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
      
      {currentPage === 'home' && <HomePage />}
      {currentPage === 'test' && <TestPage />}
      {currentPage === 'osmd' && <OSMDTest />}
    </div>
  );
};

export default App;