# 🤖 AutoJOIN Telegram Bot with Admin Dashboard

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-19.1.0-blue.svg)](https://reactjs.org)
[![Flask](https://img.shields.io/badge/Flask-2.2.5-green.svg)](https://flask.palletsprojects.com)
[![Material-UI](https://img.shields.io/badge/Material--UI-7.2.0-blue.svg)](https://mui.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A comprehensive **Telegram Bot** with a modern **React Admin Dashboard** for managing users, real-time messaging, and automated group management. Features include auto-approval, media sharing, voice messages, and a Messenger-style chat interface.

## ✨ Features

### 🤖 Core Bot Functionality
- **Auto-Approval System** - Automatically approve new group members
- **Welcome Messages** - Customizable welcome messages for new users
- **User Management** - Track and manage all bot users
- **Real-time Notifications** - Instant updates for admin actions
- **Multi-Group Support** - Manage multiple groups simultaneously

### 💬 Chat & Messaging
- **Real-time Chat** - Socket.IO powered live messaging
- **Media Support** - Images, videos, voice messages, and files
- **Message History** - Complete conversation history
- **Online Status** - Real-time user online indicators
- **Message Status** - Delivery and read receipts

### 🎨 Admin Dashboard
- **Modern React Interface** - Material-UI based responsive design
- **User Statistics** - Real-time user and message counts
- **Broadcast Messages** - Send messages to all users
- **Direct Messaging** - One-on-one chat with users
- **Activity Tracking** - Monitor user activity and engagement
- **Media Management** - Upload and share media files

### 📱 User Experience
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Dark/Light Theme** - Toggle between themes
- **Push Notifications** - Browser notifications for new messages
- **File Upload** - Drag and drop file sharing
- **Voice Recording** - Browser-based voice message recording

## 🛠️ Technology Stack

### Backend
- **Python 3.8+** - Core programming language
- **Flask** - Web framework for API
- **Flask-SocketIO** - Real-time communication
- **python-telegram-bot** - Telegram Bot API integration
- **Pyrogram** - Additional Telegram functionality
- **SQLite** - Lightweight database storage
- **Gevent** - Asynchronous networking library

### Frontend
- **React 19.1.0** - Modern JavaScript framework
- **Material-UI** - Component library for design
- **Socket.IO Client** - Real-time updates
- **Bootstrap** - Additional styling components
- **React Icons** - Icon library

### DevOps
- **Docker** - Containerization support
- **Nginx** - Web server configuration
- **Let's Encrypt** - SSL certificate management
- **Systemd** - Service management

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- Node.js 16+ and npm
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Telegram API credentials (API_ID and API_HASH)

### Quick Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/moonbd0529/autojionbot.git
   cd autojionbot
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Node.js dependencies**
   ```bash
   cd admin
   npm install
   cd ..
   ```

4. **Configure the bot**
   ```bash
   # Edit config.py with your credentials
   nano config.py
   ```

5. **Initialize the database**
   ```bash
   python db.py
   ```

## ⚙️ Configuration

### Bot Configuration (`config.py`)
```python
# Telegram Bot Token (from @BotFather)
BOT_TOKEN = 'your_bot_token_here'

# Admin User ID (your Telegram user ID)
ADMIN_USER_ID = 123456789

# Dashboard Password
DASHBOARD_PASSWORD = 'your_secure_password'

# Group and Channel IDs
GROUP_CHAT_ID = -1001234567890
CHANNEL_ID = -1002286109418
CHANNEL_URL = 'https://t.me/your_channel'

# Pyrogram Configuration
API_ID = "your_api_id"
API_HASH = "your_api_hash"

# Welcome Message
WELCOME_MESSAGE = "👋 Welcome to our Telegram group!"
```

### Environment Variables
```bash
# Create .env file
FLASK_ENV=production
API_PORT=5001
FRONTEND_URL=https://your-domain.com
API_DEBUG=false
BOT_TOKEN=your_bot_token_here
DASHBOARD_PASSWORD=your_secure_password
```

## 🚀 Running the Application

### Development Mode

1. **Start the Backend**
   ```bash
   python api-updated.py
   ```
   - Flask server runs on `http://localhost:5001`

2. **Start the Frontend**
   ```bash
   cd admin
   npm start
   ```
   - React app runs on `http://localhost:3000`

3. **Test the Setup**
   ```bash
   python test_bot.py
   ```

### Production Deployment

#### Option 1: Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d

# Check status
docker-compose ps
```

#### Option 2: Manual Deployment
```bash
# Build frontend for production
cd admin && npm run build && cd ..

# Start with systemd service
sudo systemctl start telegram-bot
sudo systemctl start nginx
```

#### Option 3: Auto Script
```bash
# Use the deployment script
chmod +x deploy.sh
./deploy.sh
```

## 📖 Usage Guide

### For Users
1. **Start a conversation** with your bot on Telegram
2. Send `/start` to begin
3. Join the configured channel/group
4. Chat with the admin through the bot

### For Admins
1. **Access Dashboard** at `http://localhost:3000`
2. **Login** with your admin credentials
3. **View Statistics** - User count, message count, activity
4. **Manage Users** - View user list, send messages
5. **Open Chat Windows** - Real-time messaging with users
6. **Send Media** - Share images, videos, voice messages
7. **Broadcast Messages** - Send to all users

### Key Features
- **Real-time Updates** - Live user activity and messages
- **Media Sharing** - Support for all file types
- **Voice Messages** - Browser-based recording
- **User Management** - Complete user control
- **Statistics Dashboard** - Analytics and insights

## 🌐 Deployment Options

### Local Development
- Backend: `http://localhost:5001`
- Frontend: `http://localhost:3000`
- Database: SQLite (local file)

### Production Server
- **Domain**: `https://your-domain.com`
- **SSL**: Let's Encrypt certificates
- **Web Server**: Nginx reverse proxy
- **Process Manager**: Systemd services

### Docker Deployment
- **Containerization**: Docker & Docker Compose
- **Port Mapping**: 80:80, 443:443, 5001:5001
- **Volume Mounts**: Database and media files
- **Network**: Isolated Docker network

## 🔧 API Endpoints

### Authentication
- `POST /login` - Admin login
- `POST /logout` - Admin logout

### Dashboard
- `GET /dashboard-stats` - Get statistics
- `GET /users` - Get user list
- `GET /messages` - Get message history

### Chat
- `POST /send-message` - Send message to user
- `POST /broadcast` - Send broadcast message
- `GET /chat-history` - Get chat history

### Media
- `POST /upload-media` - Upload media file
- `GET /media/<filename>` - Get media file

## 📊 Monitoring & Maintenance

### Service Management
```bash
# Check service status
sudo systemctl status telegram-bot nginx

# View logs
sudo journalctl -u telegram-bot -f

# Restart services
sudo systemctl restart telegram-bot nginx
```

### Database Management
```bash
# Backup database
cp users.db users.db.backup.$(date +%Y%m%d_%H%M%S)

# Check database integrity
python -c "import sqlite3; sqlite3.connect('users.db')"
```

### SSL Certificate Renewal
```bash
# Renew Let's Encrypt certificates
sudo certbot renew

# Check certificate status
sudo certbot certificates
```

## 🐛 Troubleshooting

### Common Issues

#### Bot Not Responding
```bash
# Check bot token
curl -s "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"

# Check service status
sudo systemctl status telegram-bot
```

#### Database Errors
```bash
# Fix permissions
chmod 644 users.db
chown telegrambot:telegrambot users.db

# Test database
python -c "import sqlite3; sqlite3.connect('users.db')"
```

#### CORS Errors
```bash
# Update CORS configuration
python change-api-url.py custom 0.0.0.0 5001 https://your-domain.com
```

#### Port Conflicts
```bash
# Find process using port
sudo lsof -i :5001

# Kill process
sudo kill -9 <PID>
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [Material-UI](https://mui.com/) - React component library
- [Flask](https://flask.palletsprojects.com/) - Python web framework
- [Socket.IO](https://socket.io/) - Real-time communication

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/moonbd0529/autojionbot/issues)
- **Documentation**: [Full Deployment Guide](FULL_DEPLOYMENT_GUIDE.md)
- **Email**: mushfiqurbd1701@gmail.com

---

<div align="center">
  <p>Made with ❤️ by <a href="https://github.com/moonbd0529">moonbd0529</a></p>
  <p>⭐ Star this repository if you found it helpful!</p>
</div>