# 🔧 API Server Configuration
# সহজে URL পরিবর্তন করার জন্য

import os
from typing import Dict, Any

# ========================================
# 🌐 ENVIRONMENT-BASED CONFIGURATION
# ========================================

class APIConfig:
    """API Server Configuration with environment-based URLs"""
    
    def __init__(self):
        self.environment = self._get_environment()
        self.config = self._load_config()
    
    def _get_environment(self) -> str:
        """Get current environment"""
        return os.getenv('FLASK_ENV', 'development')
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration based on environment"""
        configs = {
            'development': {
                'HOST': '0.0.0.0',
                'PORT': 5001,
                'DEBUG': True,
                'FRONTEND_URL': 'https://admin-8f9s.onrender.com',
                'CORS_ORIGINS': [
                    'https://admin-8f9s.onrender.com',
                    'https://admin-8f9s.onrender.com',
                    'https://admin-8f9s.onrender.com'
                ],
                'MEDIA_PATH': './media',
                'DATABASE_PATH': './users.db'
            },
            
            'staging': {
                'HOST': '0.0.0.0',
                'PORT': 5001,
                'DEBUG': False,
                'FRONTEND_URL': 'https://admin-8f9s.onrender.com',
                'CORS_ORIGINS': [
                    'https://admin-8f9s.onrender.com',
                    'https://staging.your-domain.com:3000'
                ],
                'MEDIA_PATH': './media',
                'DATABASE_PATH': './users.db'
            },
            
            'production': {
                'HOST': '0.0.0.0',
                'PORT': 5001,
                'DEBUG': False,
                'FRONTEND_URL': 'https://admin-8f9s.onrender.com',
                'CORS_ORIGINS': [
                    'https://admin-8f9s.onrender.com',
                    'https://admin-8f9s.onrender.com'
                ],
                'MEDIA_PATH': './media',
                'DATABASE_PATH': './users.db'
            }
        }
        
        return configs.get(self.environment, configs['development'])
    
    # ========================================
    # 🔧 CONFIGURATION GETTERS
    # ========================================
    
    @property
    def HOST(self) -> str:
        return self.config['HOST']
    
    @property
    def PORT(self) -> int:
        return self.config['PORT']
    
    @property
    def DEBUG(self) -> bool:
        return self.config['DEBUG']
    
    @property
    def FRONTEND_URL(self) -> str:
        return self.config['FRONTEND_URL']
    
    @property
    def CORS_ORIGINS(self) -> list:
        return self.config['CORS_ORIGINS']
    
    @property
    def MEDIA_PATH(self) -> str:
        return self.config['MEDIA_PATH']
    
    @property
    def DATABASE_PATH(self) -> str:
        return self.config['DATABASE_PATH']
    
    # ========================================
    # 🌐 URL HELPER METHODS
    # ========================================
    
    def get_server_url(self) -> str:
        """Get full server URL"""
        protocol = 'https' if self.environment != 'development' else 'http'
        return f"{protocol}://{self.HOST}:{self.PORT}"
    
    def get_media_url(self, filename: str) -> str:
        """Get media file URL"""
        base_url = self.get_server_url()
        return f"{base_url}/media/{filename}"
    
    def get_api_url(self, endpoint: str) -> str:
        """Get API endpoint URL"""
        base_url = self.get_server_url()
        return f"{base_url}/{endpoint.lstrip('/')}"
    
    # ========================================
    # 🔧 CONFIGURATION UPDATES
    # ========================================
    
    def update_frontend_url(self, new_url: str):
        """Update frontend URL"""
        self.config['FRONTEND_URL'] = new_url
        # Update CORS origins
        self.config['CORS_ORIGINS'] = [new_url]
        print(f"✅ Frontend URL updated to: {new_url}")
    
    def update_server_port(self, new_port: int):
        """Update server port"""
        self.config['PORT'] = new_port
        print(f"✅ Server port updated to: {new_port}")
    
    def update_environment(self, new_env: str):
        """Update environment"""
        self.environment = new_env
        self.config = self._load_config()
        print(f"✅ Environment updated to: {new_env}")
    
    # ========================================
    # 📊 CONFIGURATION INFO
    # ========================================
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get current configuration info"""
        return {
            'environment': self.environment,
            'host': self.HOST,
            'port': self.PORT,
            'debug': self.DEBUG,
            'frontend_url': self.FRONTEND_URL,
            'cors_origins': self.CORS_ORIGINS,
            'media_path': self.MEDIA_PATH,
            'database_path': self.DATABASE_PATH,
            'server_url': self.get_server_url()
        }
    
    def print_config(self):
        """Print current configuration"""
        info = self.get_config_info()
        print("🔧 Current API Configuration:")
        print("=" * 40)
        for key, value in info.items():
            print(f"{key}: {value}")
        print("=" * 40)

# ========================================
# 🚀 GLOBAL CONFIG INSTANCE
# ========================================

# Create global config instance
api_config = APIConfig()

# ========================================
# 🔧 ENVIRONMENT VARIABLES
# ========================================

# You can override these with environment variables
def load_env_config():
    """Load configuration from environment variables"""
    
    # Environment
    if os.getenv('FLASK_ENV'):
        api_config.update_environment(os.getenv('FLASK_ENV'))
    
    # Port
    if os.getenv('API_PORT'):
        api_config.update_server_port(int(os.getenv('API_PORT')))
    
    # Frontend URL
    if os.getenv('FRONTEND_URL'):
        api_config.update_frontend_url(os.getenv('FRONTEND_URL'))
    
    # Host
    if os.getenv('API_HOST'):
        api_config.config['HOST'] = os.getenv('API_HOST')
    
    # Debug
    if os.getenv('API_DEBUG'):
        api_config.config['DEBUG'] = os.getenv('API_DEBUG').lower() == 'true'

# Load environment configuration
load_env_config()

# ========================================
# 📋 USAGE EXAMPLES
# ========================================

if __name__ == "__main__":
    # Print current configuration
    api_config.print_config()
    
    # Example: Update frontend URL
    # api_config.update_frontend_url('https://new-domain.com')
    
    # Example: Update port
    # api_config.update_server_port(8000)
    
    # Example: Update environment

    # api_config.update_environment('production') 

