import React, { useState } from 'react';
import AppLayout from './components/AppLayout';
import ApiDebugger from './components/ApiDebugger';
import './App.css';

const App: React.FC = () => {
  const [showDebugger, setShowDebugger] = useState(false);

  return (
    <div className="App">
      <button 
        onClick={() => setShowDebugger(!showDebugger)}
        style={{ 
          position: 'fixed', 
          top: '10px', 
          right: '10px', 
          zIndex: 9999,
          padding: '10px',
          background: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '5px',
          cursor: 'pointer'
        }}
      >
        {showDebugger ? '隐藏调试器' : '显示调试器'}
      </button>
      
      {showDebugger && <ApiDebugger />}
      
      {!showDebugger && <AppLayout />}
    </div>
  );
};

export default App;