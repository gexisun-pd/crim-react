# 部署配置说明

## 概述
本配置解决了在使用nginx将React应用映射到域名时的跨域问题。

## 配置结构

### 1. 环境配置
- `.env.local`: 本地开发环境配置
- `.env.production`: 生产环境配置
- `src/vite-env.d.ts`: TypeScript环境变量类型定义

### 2. API配置
- `src/config/api.ts`: 统一的API配置管理
- 自动根据环境选择正确的API基础URL

### 3. Flask CORS配置
已更新`api/app.py`中的CORS配置，支持：
- 开发环境: localhost:9173, localhost:9174
- 生产环境: https://crim.gexisun.com, http://crim.gexisun.com

## 部署步骤

### 1. 构建React应用
```bash
cd react-pieces-app
npm run build
```

### 2. 启动服务
```bash
# 启动API服务器 (端口9000)
python3 api/app.py

# 启动React预览服务器 (端口9174)
cd react-pieces-app
npm run preview
```

### 3. 配置nginx
使用提供的`nginx-config-example.conf`文件配置nginx，将域名映射到端口9174。

### 4. 测试配置
- 访问 https://crim.gexisun.com 查看React应用
- API请求将自动使用localhost:9000（后端通信）
- 跨域问题已解决

## 注意事项
- API服务器保持在localhost:9000，仅供内部通信
- React应用通过nginx在域名上提供服务
- 所有硬编码的URL已替换为环境配置驱动的URL
- 支持HTTP和HTTPS域名访问
