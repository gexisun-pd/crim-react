// API configuration utility for Create React App
export const getApiBaseUrl = (): string => {
  // 检查环境变量
  const envUrl = process.env.REACT_APP_API_BASE_URL;
  console.log('环境变量 REACT_APP_API_BASE_URL:', envUrl);
  
  // 如果环境变量明确设置且不为空，使用它
  if (envUrl && envUrl.trim() !== '') {
    console.log('使用环境变量URL:', envUrl);
    return envUrl;
  }
  
  // 动态检测API URL
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    
    console.log('API Config - Current hostname:', hostname);
    console.log('API Config - Current protocol:', protocol);
    console.log('API Config - Full location:', window.location.href);
    
    // 生产环境：使用nginx代理的API路径
    if (hostname === 'crim.gexisun.com') {
      const apiUrl = `${protocol}//${hostname}/api`;
      console.log('API Config - 生产环境API URL:', apiUrl);
      return apiUrl;
    }
    
    // 开发环境或IP访问：使用直接端口
    const apiUrl = `${protocol}//${hostname}:9000`;
    console.log('API Config - 开发环境API URL:', apiUrl);
    return apiUrl;
  }
  
  // 服务器端渲染回退
  console.log('使用服务器端回退URL: http://localhost:9000');
  return 'http://localhost:9000';
};

export const getHealthCheckUrl = (): string => {
  const baseUrl = getApiBaseUrl();
  return `${baseUrl}/health`;
};
