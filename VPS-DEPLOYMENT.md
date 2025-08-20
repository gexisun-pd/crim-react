# VPS 部署配置指南

## 环境配置

### 1. 生产环境变量
创建 `.env.production.local` 文件：
```
REACT_APP_API_BASE_URL=
GENERATE_SOURCEMAP=false
```

### 2. 系统配置

#### 防火墙配置
```bash
# Ubuntu/Debian
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 9000/tcp  # API服务器（如需外部访问）

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --reload
```

#### Nginx配置 (`/etc/nginx/sites-available/crim`)
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # 重定向到HTTPS（推荐）
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL证书配置
    ssl_certificate /path/to/your/fullchain.pem;
    ssl_certificate_key /path/to/your/privkey.pem;

    # 安全headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # React应用静态文件
    location / {
        root /path/to/your/react-pieces-app/build;
        try_files $uri $uri/ /index.html;
        
        # 缓存静态资源
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API代理（可选 - 如果你想通过同一域名访问API）
    location /api/ {
        proxy_pass http://127.0.0.1:9000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers（如果需要）
        add_header Access-Control-Allow-Origin "*";
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "Origin, X-Requested-With, Content-Type, Accept, Authorization";
    }
}
```

### 3. 部署脚本 (`deploy-to-vps.sh`)
```bash
#!/bin/bash

# 构建React应用
cd react-pieces-app
npm run build

# 上传到VPS（需要配置SSH密钥）
rsync -avz --delete build/ user@your-vps:/path/to/your/app/

# 重启服务
ssh user@your-vps "sudo systemctl reload nginx"
```

### 4. 系统服务配置

#### Flask API服务 (`/etc/systemd/system/crim-api.service`)
```ini
[Unit]
Description=CRIM React API Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/your/project
Environment=FLASK_ENV=production
ExecStart=/path/to/your/venv/bin/python api/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 启用服务
```bash
sudo systemctl enable crim-api
sudo systemctl start crim-api
sudo systemctl enable nginx
```

## 安全考虑

1. **使用HTTPS** - 通过Let's Encrypt获取免费SSL证书
2. **限制API访问** - 只允许必要的来源访问API
3. **定期更新** - 保持系统和依赖项更新
4. **监控日志** - 设置日志监控和报警

## 测试部署

1. 访问 `https://your-domain.com` 确认React应用正常加载
2. 测试API功能确保数据正常获取
3. 在不同设备和网络环境下测试访问
