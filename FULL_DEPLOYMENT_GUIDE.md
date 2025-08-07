# 🚀 সম্পূর্ণ ডেপ্লয়মেন্ট গাইড
# Telegram Bot + React Admin Dashboard

## 📋 Table of Contents

1. [📋 প্রজেক্ট Overview](#-প্রজেক্ট-overview)
2. [🛠️ সার্ভার সেটআপ](#️-সার্ভার-সেটআপ)
3. [📦 প্রজেক্ট সেটআপ](#-প্রজেক্ট-সেটআপ)
4. [⚙️ কনফিগারেশন](#-কনফিগারেশন)
5. [🚀 ডেপ্লয়মেন্ট অপশন](#-ডেপ্লয়মেন্ট-অপশন)
6. [🌐 Domain & SSL](#-domain--ssl)
7. [📊 মনিটরিং](#-মনিটরিং)
8. [🔧 ট্রাবলশুটিং](#-ট্রাবলশুটিং)

---

## 📋 প্রজেক্ট Overview

### 🏗️ Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (React)       │◄──►│   (Flask API)   │◄──►│   (SQLite)      │
│   Port: 3000    │    │   Port: 5001    │    │   File: users.db│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 📦 Components
- **Backend**: Python Flask API (Telegram Bot)
- **Frontend**: React Admin Dashboard
- **Database**: SQLite
- **Real-time**: Socket.IO
- **Web Server**: Nginx
- **SSL**: Let's Encrypt

### 🌐 URLs
- **Dashboard**: `https://your-domain.com`
- **API**: `https://your-domain.com:5001`
- **Media**: `https://your-domain.com/media/`

---

## 🛠️ সার্ভার সেটআপ

### 1. সার্ভার প্রস্তুতি

#### Ubuntu/Debian (রেকমেন্ডেড)
```bash
# সিস্টেম আপডেট
sudo apt update && sudo apt upgrade -y

# প্রয়োজনীয় প্যাকেজ ইনস্টল
sudo apt install -y python3 python3-pip python3-venv nodejs npm nginx git curl wget unzip

# Node.js 18.x ইনস্টল
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Python dependencies
sudo apt install -y build-essential python3-dev libffi-dev libssl-dev
```

#### CentOS/RHEL
```bash
# সিস্টেম আপডেট
sudo yum update -y

# প্রয়োজনীয় প্যাকেজ ইনস্টল
sudo yum install -y python3 python3-pip nodejs npm nginx git curl wget

# Node.js 18.x ইনস্টল
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs
```

### 2. Firewall সেটআপ
```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5001/tcp
sudo ufw enable

# Firewalld (CentOS)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=5001/tcp
sudo firewall-cmd --reload
```

### 3. User সেটআপ
```bash
# নতুন user তৈরি
sudo adduser telegrambot
sudo usermod -aG sudo telegrambot

# User switch
su - telegrambot
```

---

## 📦 প্রজেক্ট সেটআপ

### 1. প্রজেক্ট ক্লোন
```bash
# প্রজেক্ট ক্লোন
git clone <your-repository-url>
cd auto-join

# Permissions সেট
sudo chown -R $USER:$USER .
```

### 2. Backend সেটআপ
```bash
# Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Dependencies ইনস্টল
pip install -r requirements.txt

# Additional production dependencies
pip install gunicorn gevent

# Media directory তৈরি
mkdir -p media
chmod 755 media
```

### 3. Frontend সেটআপ
```bash
# Node.js dependencies
cd admin
npm install

# Production build
npm run build
cd ..
```

### 4. Database সেটআপ
```bash
# Database permissions
chmod 644 users.db 2>/dev/null || true

# Test database connection
python3 -c "import sqlite3; sqlite3.connect('users.db')"
```

---

## ⚙️ কনফিগারেশন

### 1. Backend Configuration

#### `config.py` ফাইল এডিট করুন:
```python
# Telegram Bot Token (BotFather থেকে নিন)
BOT_TOKEN = "your_bot_token_here"

# Dashboard Password
DASHBOARD_PASSWORD = "your_secure_password"

# Channel/Group ID
CHANNEL_ID = -1001234567890  # আপনার চ্যানেল/গ্রুপ ID

# Invite Link
GROUP_INVITE_LINK = "https://t.me/your_group_invite_link"

# Channel URL
CHANNEL_URL = "https://t.me/your_channel"

# Pyrogram কনফিগারেশন (যদি ব্যবহার করেন)
API_ID = "your_api_id"
API_HASH = "your_api_hash"
```

#### API Configuration (`api_config.py`):
```python
# Production environment
'production': {
    'HOST': '0.0.0.0',
    'PORT': 5001,
    'DEBUG': False,
    'FRONTEND_URL': 'https://your-domain.com',
    'CORS_ORIGINS': [
        'https://your-domain.com',
        'https://www.your-domain.com'
    ]
}
```

### 2. Frontend Configuration

#### `admin/src/environment.js` ফাইল এডিট করুন:
```javascript
production: {
    API_BASE_URL: 'https://your-domain.com:5001',
    SOCKET_URL: 'https://your-domain.com:5001',
    MEDIA_BASE_URL: 'https://your-domain.com:5001/media',
    FRONTEND_URL: 'https://your-domain.com'
}
```

### 3. Environment Variables
```bash
# .env ফাইল তৈরি করুন
cat > .env << EOF
FLASK_ENV=production
API_PORT=5001
FRONTEND_URL=https://your-domain.com
API_DEBUG=false
BOT_TOKEN=your_bot_token_here
DASHBOARD_PASSWORD=your_secure_password
EOF
```

---

## 🚀 ডেপ্লয়মেন্ট অপশন

### অপশন 1: Auto Script (সবচেয়ে সহজ)

```bash
# Script executable করুন
chmod +x deploy.sh

# ডেপ্লয় করুন
./deploy.sh
```

### অপশন 2: Manual Deployment

#### Step 1: Systemd Service তৈরি
```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Service ফাইলে লিখুন:
```ini
[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
Type=simple
User=telegrambot
WorkingDirectory=/home/telegrambot/auto-join
Environment=PATH=/home/telegrambot/auto-join/venv/bin
Environment=FLASK_ENV=production
Environment=API_PORT=5001
Environment=FRONTEND_URL=https://your-domain.com
ExecStart=/home/telegrambot/auto-join/venv/bin/python api-updated.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Step 2: Service চালু
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

### অপশন 3: Docker Deployment

#### Docker Compose (`docker-compose.yml`):
```yaml
version: '3.8'

services:
  telegram-bot:
    build: .
    container_name: telegram-bot
    restart: unless-stopped
    ports:
      - "5001:5001"
    volumes:
      - ./users.db:/app/users.db
      - ./media:/app/media
      - ./config.py:/app/config.py
    environment:
      - FLASK_ENV=production
      - API_PORT=5001
      - FRONTEND_URL=https://your-domain.com
    networks:
      - bot-network

  nginx:
    image: nginx:alpine
    container_name: telegram-bot-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./admin/build:/usr/share/nginx/html
      - ./media:/usr/share/nginx/media
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - telegram-bot
    networks:
      - bot-network

networks:
  bot-network:
    driver: bridge
```

#### Docker চালু:
```bash
# Build এবং চালু
docker-compose up -d

# Status চেক
docker-compose ps

# Logs দেখুন
docker-compose logs -f
```

---

## 🌐 Nginx Configuration

### 1. Nginx কনফিগারেশন
```bash
sudo nano /etc/nginx/sites-available/telegram-bot
```

কনফিগারেশন লিখুন:
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Frontend (React build)
    location / {
        root /home/telegrambot/auto-join/admin/build;
        try_files $uri $uri/ /index.html;
        
        # Cache static files
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:5001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Media files
    location /media/ {
        alias /home/telegrambot/auto-join/media/;
        expires 1d;
        add_header Cache-Control "public";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
}
```

### 2. Nginx এনাবল
```bash
# Default site disable
sudo rm -f /etc/nginx/sites-enabled/default

# New site enable
sudo ln -s /etc/nginx/sites-available/telegram-bot /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

---

## 🔒 SSL/HTTPS Setup

### 1. Let's Encrypt SSL
```bash
# Certbot ইনস্টল
sudo apt install certbot python3-certbot-nginx

# SSL সার্টিফিকেট জেনারেট
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal সেটআপ
sudo crontab -e
# Add this line: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. Manual SSL (যদি নিজের সার্টিফিকেট থাকে)
```bash
# SSL directory তৈরি
sudo mkdir -p /etc/nginx/ssl

# Certificates কপি
sudo cp your-cert.pem /etc/nginx/ssl/
sudo cp your-key.pem /etc/nginx/ssl/

# Permissions সেট
sudo chmod 600 /etc/nginx/ssl/*
```

### 3. HTTPS Nginx Configuration
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Same location blocks as HTTP
    location / {
        root /home/telegrambot/auto-join/admin/build;
        try_files $uri $uri/ /index.html;
    }
    
    location /api/ {
        proxy_pass http://127.0.0.1:5001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /media/ {
        alias /home/telegrambot/auto-join/media/;
        expires 1d;
    }
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 📊 মনিটরিং

### 1. Service Status
```bash
# Service status
sudo systemctl status telegram-bot

# Service logs
sudo journalctl -u telegram-bot -f

# Service restart
sudo systemctl restart telegram-bot
```

### 2. Process Monitoring
```bash
# Running processes
ps aux | grep python

# Port listening
netstat -tlnp | grep 5001

# Memory usage
free -h

# Disk usage
df -h
```

### 3. Log Monitoring
```bash
# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Application logs
sudo journalctl -u telegram-bot --no-pager -l -n 50

# Docker logs (if using Docker)
docker-compose logs -f
```

### 4. Performance Monitoring
```bash
# System resources
htop

# Network connections
ss -tulpn

# Disk I/O
iotop
```

---

## 🔧 ট্রাবলশুটিং

### 1. Common Issues

#### Bot Token Error
```bash
# Check config.py
nano config.py

# Verify bot token
curl -s "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"
```

#### Database Error
```bash
# Check database permissions
ls -la users.db

# Fix permissions
chmod 644 users.db
chown telegrambot:telegrambot users.db

# Test database
python3 -c "import sqlite3; sqlite3.connect('users.db')"
```

#### Port Already in Use
```bash
# Find process using port
sudo lsof -i :5001

# Kill process
sudo kill -9 <PID>

# Or change port
export API_PORT=8000
```

#### CORS Errors
```bash
# Check CORS configuration
python change-api-url.py test

# Update CORS origins
python change-api-url.py custom 0.0.0.0 5001 https://your-domain.com
```

### 2. Service Issues

#### Service Not Starting
```bash
# Check service status
sudo systemctl status telegram-bot

# Check logs
sudo journalctl -u telegram-bot --no-pager -l

# Test manually
cd /home/telegrambot/auto-join
source venv/bin/activate
python api-updated.py
```

#### Nginx Issues
```bash
# Test Nginx configuration
sudo nginx -t

# Check Nginx status
sudo systemctl status nginx

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### 3. SSL Issues

#### SSL Certificate Expired
```bash
# Renew certificate
sudo certbot renew

# Check certificate status
sudo certbot certificates

# Test SSL
curl -I https://your-domain.com
```

#### SSL Configuration Error
```bash
# Check SSL configuration
sudo nginx -t

# Verify certificate
openssl x509 -in /etc/letsencrypt/live/your-domain.com/fullchain.pem -text -noout
```

### 4. Performance Issues

#### High Memory Usage
```bash
# Check memory usage
free -h

# Find memory-hungry processes
ps aux --sort=-%mem | head -10

# Restart service
sudo systemctl restart telegram-bot
```

#### High CPU Usage
```bash
# Check CPU usage
top

# Find CPU-hungry processes
ps aux --sort=-%cpu | head -10

# Check for infinite loops
sudo journalctl -u telegram-bot --no-pager -l | grep -i error
```

---

## 🚀 Quick Deployment Commands

### 1. Full Auto Deployment
```bash
# Clone and setup
git clone <your-repo>
cd auto-join
chmod +x deploy.sh
./deploy.sh

# Configure
nano config.py
nano admin/src/environment.js

# Start services
sudo systemctl start telegram-bot
sudo systemctl start nginx
```

### 2. Docker Deployment
```bash
# Build and run
cd auto-join
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f
```

### 3. Manual Deployment
```bash
# Setup environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Build frontend
cd admin && npm install && npm run build && cd ..

# Configure
nano config.py
python change-api-url.py prod

# Start service
sudo systemctl start telegram-bot
```

---

## 📞 Support Commands

### 1. Status Check
```bash
# Service status
sudo systemctl status telegram-bot nginx

# Process status
ps aux | grep -E "(python|nginx)"

# Port status
netstat -tlnp | grep -E "(80|443|5001)"
```

### 2. Log Check
```bash
# Application logs
sudo journalctl -u telegram-bot -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

### 3. Configuration Check
```bash
# Test configuration
python change-api-url.py test

# Check environment
echo $FLASK_ENV
echo $API_PORT
echo $FRONTEND_URL

# Test API
curl http://localhost:5001/dashboard-stats
```

---

## 🎉 Success Checklist

- [ ] ✅ Server setup completed
- [ ] ✅ Dependencies installed
- [ ] ✅ Configuration updated
- [ ] ✅ Frontend built
- [ ] ✅ Backend running
- [ ] ✅ Nginx configured
- [ ] ✅ SSL certificate installed
- [ ] ✅ Domain pointing to server
- [ ] ✅ Dashboard accessible
- [ ] ✅ Bot responding
- [ ] ✅ Media uploads working
- [ ] ✅ Real-time chat working
- [ ] ✅ Monitoring setup
- [ ] ✅ Backup configured

---

## 📚 Additional Resources

### Useful Commands
```bash
# Restart everything
sudo systemctl restart telegram-bot nginx

# Check all services
sudo systemctl status telegram-bot nginx

# View all logs
sudo journalctl -u telegram-bot -f & sudo tail -f /var/log/nginx/access.log

# Backup database
cp users.db users.db.backup.$(date +%Y%m%d_%H%M%S)
```

### Emergency Commands
```bash
# Emergency stop
sudo systemctl stop telegram-bot

# Emergency restart
sudo systemctl restart telegram-bot

# Check what's wrong
sudo journalctl -u telegram-bot --no-pager -l -n 100
```

এই গাইড অনুসরণ করে আপনি যেকোনো সার্ভারে আপনার Telegram Bot সহজে ডেপ্লয় করতে পারবেন! 🚀 