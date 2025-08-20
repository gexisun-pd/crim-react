import React, { useState, useEffect } from 'react';
import AppLayout from './components/AppLayout';
import ApiDebugger from './components/ApiDebugger';
import './App.css';

const App: React.FC = () => {
  const [showDebugger, setShowDebugger] = useState(false);

  // 检查URL参数来决定是否显示调试器
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('debug') === 'true') {
      setShowDebugger(true);
    }
    
    // 添加键盘快捷键 Ctrl+Shift+D 来切换调试器
    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.shiftKey && event.key === 'D') {
        setShowDebugger(prev => !prev);
      }
    };
    
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  return (
    <div className="App">
      {/* 调试器按钮被隐藏，但保留调试器功能 */}
      {/* 可以通过 ?debug=true 或 Ctrl+Shift+D 访问调试器 */}
      
      {showDebugger && <ApiDebugger onClose={() => setShowDebugger(false)} />}
      
      {!showDebugger && <AppLayout />}
    </div>
  );
};

export default App;