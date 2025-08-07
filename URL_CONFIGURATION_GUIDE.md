# 🔗 URL Configuration Guide
# এক জায়গায় পরিবর্তন করলেই সব জায়গায় পরিবর্তন হবে

## 📋 Overview

এই সিস্টেমে আপনি শুধু একটি জায়গায় URL পরিবর্তন করলেই সব জায়গায় পরিবর্তন হবে। তিনটি environment এর জন্য আলাদা URL সেট করা যায়:

- **Development**: Local development এর জন্য
- **Staging**: Testing এর জন্য  
- **Production**: Live server এর জন্য

## 🚀 Quick Start

### 1. Development URL পরিবর্তন
```javascript
// admin/src/environment.js ফাইলে
const URLS = {
  development: {
    API_BASE_URL: 'http://localhost:5001',  // এখানে পরিবর্তন করুন
    SOCKET_URL: 'http://localhost:5001',    // এখানে পরিবর্তন করুন
    MEDIA_BASE_URL: 'http://localhost:5001/media',
    FRONTEND_URL: 'http://localhost:3000'
  },
  // ...
};
```

### 2. Production URL পরিবর্তন
```javascript
// admin/src/environment.js ফাইলে
const URLS = {
  production: {
    API_BASE_URL: 'https://your-domain.com',  // এখানে পরিবর্তন করুন
    SOCKET_URL: 'https://your-domain.com',    // এখানে পরিবর্তন করুন
    MEDIA_BASE_URL: 'https://your-domain.com/media',
    FRONTEND_URL: 'https://your-domain.com'
  },
  // ...
};
```

## 🔧 Configuration Files

### 1. Environment Configuration (`admin/src/environment.js`)
```javascript
const URLS = {
  development: {
    API_BASE_URL: 'http://localhost:5001',
    SOCKET_URL: 'http://localhost:5001',
    MEDIA_BASE_URL: 'http://localhost:5001/media',
    FRONTEND_URL: 'http://localhost:3000'
  },
  
  staging: {
    API_BASE_URL: 'https://staging.your-domain.com',
    SOCKET_URL: 'https://staging.your-domain.com',
    MEDIA_BASE_URL: 'https://staging.your-domain.com/media',
    FRONTEND_URL: 'https://staging.your-domain.com'
  },
  
  production: {
    API_BASE_URL: 'https://your-domain.com',
    SOCKET_URL: 'https://your-domain.com',
    MEDIA_BASE_URL: 'https://your-domain.com/media',
    FRONTEND_URL: 'https://your-domain.com'
  }
};
```

### 2. Main Configuration (`admin/src/config.js`)
```javascript
import environmentConfig from './environment.js';

const config = {
  API_BASE_URL: environmentConfig.API_BASE_URL,
  SOCKET_URL: environmentConfig.SOCKET_URL,
  MEDIA_BASE_URL: environmentConfig.MEDIA_BASE_URL,
  FRONTEND_URL: environmentConfig.FRONTEND_URL,
  
  // Helper functions
  getMediaUrl: (url) => {
    if (url.startsWith('http')) return url;
    return `${environmentConfig.API_BASE_URL}${url}`;
  },
  
  getApiUrl: (endpoint) => {
    return `${environmentConfig.API_BASE_URL}/${endpoint}`;
  }
};
```

## 🌐 URL Change Examples

### Development থেকে Production এ পরিবর্তন

#### Before (Development):
```javascript
API_BASE_URL: 'http://localhost:5001'
SOCKET_URL: 'http://localhost:5001'
```

#### After (Production):
```javascript
API_BASE_URL: 'https://your-domain.com'
SOCKET_URL: 'https://your-domain.com'
```

### Domain পরিবর্তন

#### Before:
```javascript
API_BASE_URL: 'https://old-domain.com'
```

#### After:
```javascript
API_BASE_URL: 'https://new-domain.com'
```

### Port পরিবর্তন

#### Before:
```javascript
API_BASE_URL: 'http://localhost:5001'
```

#### After:
```javascript
API_BASE_URL: 'http://localhost:8000'
```

## 🔄 Automatic URL Detection

সিস্টেমটি automatically environment detect করে:

```javascript
const getEnvironment = () => {
  // Check hostname
  const hostname = window.location.hostname;
  
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'development';
  }
  
  if (hostname.includes('staging')) {
    return 'staging';
  }
  
  return 'production';
};
```

## 📊 URL Helper Functions

### 1. Media URL Helper
```javascript
config.getMediaUrl('/media/image.jpg')
// Returns: 'https://your-domain.com/media/image.jpg'
```

### 2. API URL Helper
```javascript
config.getApiUrl('users')
// Returns: 'https://your-domain.com/users'
```

### 3. Full URL Helper
```javascript
config.getFullUrl('api/chat')
// Returns: 'https://your-domain.com/api/chat'
```

## 🎯 Common Use Cases

### 1. Local Development
```javascript
// admin/src/environment.js
development: {
  API_BASE_URL: 'http://localhost:5001',
  SOCKET_URL: 'http://localhost:5001',
  MEDIA_BASE_URL: 'http://localhost:5001/media',
  FRONTEND_URL: 'http://localhost:3000'
}
```

### 2. Production Server
```javascript
// admin/src/environment.js
production: {
  API_BASE_URL: 'https://your-domain.com',
  SOCKET_URL: 'https://your-domain.com',
  MEDIA_BASE_URL: 'https://your-domain.com/media',
  FRONTEND_URL: 'https://your-domain.com'
}
```

### 3. Staging Server
```javascript
// admin/src/environment.js
staging: {
  API_BASE_URL: 'https://staging.your-domain.com',
  SOCKET_URL: 'https://staging.your-domain.com',
  MEDIA_BASE_URL: 'https://staging.your-domain.com/media',
  FRONTEND_URL: 'https://staging.your-domain.com'
}
```

## 🔧 URL Manager Functions

### 1. Quick URL Changes
```javascript
import urlManager from './urlManager.js';

// Development URL সেট করুন
urlManager.setDevelopmentUrl('http://localhost:8000');

// Production URL সেট করুন
urlManager.setProductionUrl('your-domain.com');

// Staging URL সেট করুন
urlManager.setStagingUrl('your-domain.com');
```

### 2. URL Validation
```javascript
// URL ভ্যালিড কিনা চেক করুন
urlManager.isValidUrl('https://your-domain.com'); // true

// Domain ভ্যালিড কিনা চেক করুন
urlManager.isValidDomain('your-domain.com'); // true
```

### 3. URL Transformation
```javascript
// HTTP থেকে HTTPS
urlManager.toHttps('http://your-domain.com');
// Returns: 'https://your-domain.com'

// Port পরিবর্তন
urlManager.changePort('http://localhost:5001', '8000');
// Returns: 'http://localhost:8000'
```

## 📝 Configuration Steps

### Step 1: Environment Detection
```javascript
// admin/src/environment.js
const getEnvironment = () => {
  if (process.env.REACT_APP_ENV) {
    return process.env.REACT_APP_ENV;
  }
  
  const hostname = window.location.hostname;
  if (hostname === 'localhost') return 'development';
  if (hostname.includes('staging')) return 'staging';
  return 'production';
};
```

### Step 2: URL Configuration
```javascript
// admin/src/environment.js
const URLS = {
  development: {
    API_BASE_URL: 'http://localhost:5001',
    SOCKET_URL: 'http://localhost:5001',
    MEDIA_BASE_URL: 'http://localhost:5001/media',
    FRONTEND_URL: 'http://localhost:3000'
  },
  // Add your URLs here
};
```

### Step 3: Import in Components
```javascript
// Any component file
import config from './config.js';

// Use URLs
const apiUrl = config.API_BASE_URL;
const mediaUrl = config.getMediaUrl('/media/file.jpg');
```

## 🚨 Troubleshooting

### 1. URL Not Changing
- Check if you're editing the correct file (`admin/src/environment.js`)
- Clear browser cache
- Restart development server

### 2. CORS Errors
- Make sure API_BASE_URL matches your backend server
- Check if backend CORS settings allow your frontend URL

### 3. Media Files Not Loading
- Verify MEDIA_BASE_URL is correct
- Check if media files exist in the specified path

## 📊 Monitoring

### 1. Check Current URLs
```javascript
import config from './config.js';

console.log('Current URLs:', {
  api: config.API_BASE_URL,
  socket: config.SOCKET_URL,
  media: config.MEDIA_BASE_URL,
  frontend: config.FRONTEND_URL
});
```

### 2. Environment Info
```javascript
console.log('Environment:', config.getEnvironment());
console.log('Is Development:', config.isDevelopment());
console.log('Is Production:', config.isProduction());
```

## 🎉 Benefits

1. **Single Point of Change**: এক জায়গায় পরিবর্তন করলেই সব জায়গায় পরিবর্তন হয়
2. **Environment Aware**: Automatically environment detect করে
3. **Type Safe**: URL validation built-in
4. **Easy Migration**: Development থেকে Production এ সহজে migrate করা যায়
5. **Maintainable**: Clean এবং organized code structure

এই সিস্টেম ব্যবহার করে আপনি সহজে যেকোনো URL পরিবর্তন করতে পারবেন! 🚀 