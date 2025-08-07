# 🔧 API Server URL পরিবর্তন করার গাইড
# সহজে API server এর URL পরিবর্তন করার জন্য

## 📋 Overview

এই গাইডে আপনি API server এ URL পরিবর্তন করার বিভিন্ন পদ্ধতি শিখবেন:

1. **Environment Variables** (সবচেয়ে ভালো পদ্ধতি)
2. **Configuration File** (Manual পরিবর্তন)
3. **Script দিয়ে** (Automated পরিবর্তন)
4. **Environment-based** (Automatic detection)

## 🚀 Quick Start

### 1. Environment Variables দিয়ে

```bash
# Development
export FLASK_ENV=development
export API_PORT=5001
export FRONTEND_URL=http://localhost:3000

# Production
export FLASK_ENV=production
export API_PORT=5001
export FRONTEND_URL=https://your-domain.com

# Server চালু করুন
python api-updated.py
```

### 2. Script দিয়ে পরিবর্তন

```bash
# Development environment
python change-api-url.py dev

# Production environment
python change-api-url.py prod

# Custom URLs
python change-api-url.py custom 0.0.0.0 8000 https://my-domain.com
```

### 3. Manual পরিবর্তন

```python
# api_config.py ফাইলে
production: {
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

## 🔧 Configuration Files

### 1. API Configuration (`api_config.py`)

```python
class APIConfig:
    def __init__(self):
        self.environment = self._get_environment()
        self.config = self._load_config()
    
    def _load_config(self):
        configs = {
            'development': {
                'HOST': '0.0.0.0',
                'PORT': 5001,
                'DEBUG': True,
                'FRONTEND_URL': 'http://localhost:3000',
                'CORS_ORIGINS': [
                    'http://localhost:3000',
                    'http://127.0.0.1:3000'
                ]
            },
            
            'production': {
                'HOST': '0.0.0.0',
                'PORT': 5001,
                'DEBUG': False,
                'FRONTEND_URL': 'https://your-domain.com',
                'CORS_ORIGINS': [
                    'https://your-domain.com'
                ]
            }
        }
        return configs.get(self.environment, configs['development'])
```

### 2. Updated API Server (`api-updated.py`)

```python
from api_config import api_config

app = Flask(__name__)

# Use configuration from api_config
CORS(app, origins=api_config.CORS_ORIGINS, supports_credentials=True)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins=api_config.CORS_ORIGINS)

if __name__ == '__main__':
    socketio.run(
        app, 
        host=api_config.HOST, 
        port=api_config.PORT, 
        debug=api_config.DEBUG
    )
```

## 🌐 URL Change Examples

### Development থেকে Production এ

#### Before (Development):
```python
'development': {
    'HOST': '0.0.0.0',
    'PORT': 5001,
    'DEBUG': True,
    'FRONTEND_URL': 'http://localhost:3000',
    'CORS_ORIGINS': ['http://localhost:3000']
}
```

#### After (Production):
```python
'production': {
    'HOST': '0.0.0.0',
    'PORT': 5001,
    'DEBUG': False,
    'FRONTEND_URL': 'https://your-domain.com',
    'CORS_ORIGINS': ['https://your-domain.com']
}
```

### Port পরিবর্তন

#### Before:
```python
'PORT': 5001
```

#### After:
```python
'PORT': 8000
```

### Domain পরিবর্তন

#### Before:
```python
'FRONTEND_URL': 'https://old-domain.com'
```

#### After:
```python
'FRONTEND_URL': 'https://new-domain.com'
```

## 🔄 Environment Variables

### 1. Set Environment Variables

```bash
# Development
export FLASK_ENV=development
export API_PORT=5001
export FRONTEND_URL=http://localhost:3000
export API_DEBUG=true

# Production
export FLASK_ENV=production
export API_PORT=5001
export FRONTEND_URL=https://your-domain.com
export API_DEBUG=false
```

### 2. .env File দিয়ে

```bash
# .env ফাইল তৈরি করুন
FLASK_ENV=production
API_PORT=5001
FRONTEND_URL=https://your-domain.com
API_DEBUG=false
```

### 3. Systemd Service দিয়ে

```ini
# /etc/systemd/system/telegram-bot.service
[Service]
Environment=FLASK_ENV=production
Environment=API_PORT=5001
Environment=FRONTEND_URL=https://your-domain.com
Environment=API_DEBUG=false
```

## 🎯 Script Commands

### 1. Show Current Configuration
```bash
python change-api-url.py show
```

### 2. Change Environment
```bash
python change-api-url.py dev      # Development
python change-api-url.py staging  # Staging
python change-api-url.py prod     # Production
```

### 3. Set Custom URLs
```bash
python change-api-url.py custom 0.0.0.0 8000 https://my-domain.com
python change-api-url.py custom localhost 5001 http://localhost:3000 true
```

### 4. Test Configuration
```bash
python change-api-url.py test
```

## 📊 Configuration Methods

### 1. Environment-based (Automatic)

```python
def _get_environment(self):
    return os.getenv('FLASK_ENV', 'development')

def _load_config(self):
    configs = {
        'development': {...},
        'production': {...}
    }
    return configs.get(self.environment, configs['development'])
```

### 2. Environment Variables (Flexible)

```python
def load_env_config():
    if os.getenv('FLASK_ENV'):
        api_config.update_environment(os.getenv('FLASK_ENV'))
    
    if os.getenv('API_PORT'):
        api_config.update_server_port(int(os.getenv('API_PORT')))
    
    if os.getenv('FRONTEND_URL'):
        api_config.update_frontend_url(os.getenv('FRONTEND_URL'))
```

### 3. Manual Configuration (Direct)

```python
# api_config.py ফাইলে সরাসরি পরিবর্তন
'production': {
    'HOST': '0.0.0.0',
    'PORT': 5001,
    'DEBUG': False,
    'FRONTEND_URL': 'https://your-domain.com',
    'CORS_ORIGINS': ['https://your-domain.com']
}
```

## 🔧 Helper Functions

### 1. URL Generation
```python
def get_server_url(self):
    protocol = 'https' if self.environment != 'development' else 'http'
    return f"{protocol}://{self.HOST}:{self.PORT}"

def get_media_url(self, filename):
    base_url = self.get_server_url()
    return f"{base_url}/media/{filename}"

def get_api_url(self, endpoint):
    base_url = self.get_server_url()
    return f"{base_url}/{endpoint.lstrip('/')}"
```

### 2. Configuration Updates
```python
def update_frontend_url(self, new_url):
    self.config['FRONTEND_URL'] = new_url
    self.config['CORS_ORIGINS'] = [new_url]

def update_server_port(self, new_port):
    self.config['PORT'] = new_port

def update_environment(self, new_env):
    self.environment = new_env
    self.config = self._load_config()
```

## 🎯 Common Scenarios

### 1. Local Development
```bash
# Environment variables
export FLASK_ENV=development
export API_PORT=5001
export FRONTEND_URL=http://localhost:3000

# Script দিয়ে
python change-api-url.py dev

# Server চালু
python api-updated.py
```

### 2. Production Server
```bash
# Environment variables
export FLASK_ENV=production
export API_PORT=5001
export FRONTEND_URL=https://your-domain.com

# Script দিয়ে
python change-api-url.py prod

# Server চালু
python api-updated.py
```

### 3. Custom Configuration
```bash
# Custom URLs
python change-api-url.py custom 0.0.0.0 8000 https://my-domain.com

# Environment variables
export API_HOST=0.0.0.0
export API_PORT=8000
export FRONTEND_URL=https://my-domain.com
```

## 🚨 Troubleshooting

### 1. CORS Errors
```python
# CORS origins আপডেট করুন
'CORS_ORIGINS': [
    'https://your-domain.com',
    'https://www.your-domain.com'
]
```

### 2. Port Already in Use
```bash
# Port পরিবর্তন করুন
python change-api-url.py custom 0.0.0.0 8000 https://your-domain.com

# অথবা environment variable দিয়ে
export API_PORT=8000
```

### 3. Configuration Not Loading
```bash
# Configuration test করুন
python change-api-url.py test

# Environment variables চেক করুন
echo $FLASK_ENV
echo $API_PORT
echo $FRONTEND_URL
```

## 📊 Monitoring

### 1. Check Current Configuration
```python
from api_config import api_config

print("Current Configuration:")
print(f"Environment: {api_config.environment}")
print(f"Host: {api_config.HOST}")
print(f"Port: {api_config.PORT}")
print(f"Frontend URL: {api_config.FRONTEND_URL}")
print(f"CORS Origins: {api_config.CORS_ORIGINS}")
```

### 2. Server Status
```bash
# Server running কিনা চেক করুন
ps aux | grep python

# Port listening কিনা চেক করুন
netstat -tlnp | grep 5001

# Logs দেখুন
tail -f /var/log/telegram-bot.log
```

## 🎉 Benefits

1. **Environment-based**: Automatically environment detect করে
2. **Flexible**: Environment variables দিয়ে সহজে পরিবর্তন
3. **Script Support**: Command line দিয়ে automated পরিবর্তন
4. **Type Safe**: Configuration validation built-in
5. **Maintainable**: Clean এবং organized structure

## 📞 Support

যদি কোনো সমস্যা হয়:
1. `python change-api-url.py test` চালান
2. Environment variables চেক করুন
3. Configuration files verify করুন
4. Server logs দেখুন

এই সিস্টেম ব্যবহার করে আপনি সহজে API server এর URL পরিবর্তন করতে পারবেন! 🚀 