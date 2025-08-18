# Flask + React 项目运行指南

## 项目结构
```
/home/sungexi/Magistrale/Tesi/agosto/
├── api/                    # Flask 后端
│   ├── app.py              # Flask 应用主文件
│   ├── requirements.txt    # Python 依赖
│   └── routes/
│       └── pieces.py       # API 路由
├── react-pieces-app/       # React 前端
│   ├── package.json        # Node.js 依赖
│   ├── src/
│   │   ├── components/     # React 组件
│   │   ├── services/       # API 服务
│   │   └── pages/          # 页面组件
│   └── public/
└── core/                   # 现有 Python 业务逻辑
    └── db/db.py            # 数据库访问类
```

## 运行步骤

### 1. 安装 Flask 后端依赖
```bash
cd /home/sungexi/Magistrale/Tesi/agosto
python -m pip install flask flask-cors
# 或者
python -m pip install -r api/requirements.txt
```

### 2. 启动 Flask API 服务器
```bash
cd /home/sungexi/Magistrale/Tesi/agosto
python api/app.py
```
Flask 服务器将在 http://localhost:5000 运行

### 3. 安装 React 前端依赖
```bash
cd /home/sungexi/Magistrale/Tesi/agosto/react-pieces-app
npm install
```

### 4. 启动 React 开发服务器
```bash
cd /home/sungexi/Magistrale/Tesi/agosto/react-pieces-app
npm start
```
React 应用将在 http://localhost:3000 运行

## API 端点

Flask API 提供以下端点：
- `GET /api/pieces` - 获取所有乐曲
- `GET /api/pieces/<id>` - 获取特定乐曲
- `GET /api/note-sets` - 获取所有音符集
- `GET /api/pieces/<id>/notes?note_set_id=<id>` - 获取乐曲的音符
- `GET /health` - 健康检查

## 功能特点

✅ **现有功能**:
- shadcn/ui 风格的现代 UI
- Tailwind CSS 样式系统
- 下拉选择器 (ComboBox) 选择乐曲
- Flask API 集成现有的数据库和业务逻辑
- CORS 支持跨域请求

✅ **技术栈**:
- **后端**: Flask + 现有 Python 核心逻辑
- **前端**: React 18 + TypeScript + Tailwind CSS + shadcn/ui
- **数据库**: SQLite (现有)

## 下一步扩展

可以考虑添加：
- 音符可视化组件
- 更多筛选选项
- 分析结果展示
- 数据导出功能

## 故障排除

如果遇到 CORS 错误，确保：
1. Flask 应用已启动在 5000 端口
2. React 应用已启动在 3000 端口 
3. flask-cors 已正确安装和配置
