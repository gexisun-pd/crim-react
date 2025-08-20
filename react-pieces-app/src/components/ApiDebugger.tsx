import React, { useState, useEffect } from 'react';
import { getApiBaseUrl, getHealthCheckUrl } from '../config/api';

const ApiDebugger: React.FC = () => {
  const [debugInfo, setDebugInfo] = useState<any>({});
  const [apiResponse, setApiResponse] = useState<string>('');
  const [healthResponse, setHealthResponse] = useState<string>('');

  useEffect(() => {
    // 收集调试信息
    const info = {
      windowLocation: typeof window !== 'undefined' ? {
        hostname: window.location.hostname,
        protocol: window.location.protocol,
        port: window.location.port,
        href: window.location.href
      } : 'N/A',
      apiBaseUrl: getApiBaseUrl(),
      healthCheckUrl: getHealthCheckUrl(),
      envVar: process.env.REACT_APP_API_BASE_URL || 'Not set',
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'N/A'
    };
    setDebugInfo(info);
  }, []);

  const testApiCall = async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/pieces`);
      const data = await response.json();
      setApiResponse(`Status: ${response.status}\nData: ${JSON.stringify(data, null, 2)}`);
    } catch (error) {
      setApiResponse(`Error: ${error}`);
    }
  };

  const testHealthCheck = async () => {
    try {
      const response = await fetch(getHealthCheckUrl());
      const data = await response.json();
      setHealthResponse(`Status: ${response.status}\nData: ${JSON.stringify(data, null, 2)}`);
    } catch (error) {
      setHealthResponse(`Error: ${error}`);
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h2>API 调试信息</h2>
      
      <h3>环境信息:</h3>
      <pre style={{ background: '#f5f5f5', padding: '10px', overflow: 'auto' }}>
        {JSON.stringify(debugInfo, null, 2)}
      </pre>

      <h3>API 测试:</h3>
      <button onClick={testApiCall} style={{ margin: '10px', padding: '10px' }}>
        测试 /api/pieces
      </button>
      <pre style={{ background: '#f0f0f0', padding: '10px', minHeight: '100px', overflow: 'auto' }}>
        {apiResponse || '点击按钮测试 API 调用'}
      </pre>

      <h3>健康检查测试:</h3>
      <button onClick={testHealthCheck} style={{ margin: '10px', padding: '10px' }}>
        测试 /health
      </button>
      <pre style={{ background: '#f0f0f0', padding: '10px', minHeight: '100px', overflow: 'auto' }}>
        {healthResponse || '点击按钮测试健康检查'}
      </pre>
    </div>
  );
};

export default ApiDebugger;
