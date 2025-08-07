#!/usr/bin/env python3

# 🔧 API Server URL Change Script
# সহজে API server এর URL পরিবর্তন করার জন্য

import os
import sys
import json
from typing import Dict, Any

# ========================================
# 🌐 URL CONFIGURATIONS
# ========================================

URL_CONFIGS = {
    'development': {
        'HOST': '0.0.0.0',
        'PORT': 5001,
        'DEBUG': True,
        'FRONTEND_URL': 'http://localhost:3000',
        'CORS_ORIGINS': [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://192.168.1.3:3000'
        ]
    },
    
    'staging': {
        'HOST': '0.0.0.0',
        'PORT': 5001,
        'DEBUG': False,
        'FRONTEND_URL': 'https://staging.your-domain.com',
        'CORS_ORIGINS': [
            'https://staging.your-domain.com',
            'https://staging.your-domain.com:3000'
        ]
    },
    
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
}

# ========================================
# 🔧 HELPER FUNCTIONS
# ========================================

def print_colored(text: str, color: str = 'white'):
    """Print colored text"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'reset': '\033[0m'
    }
    print(f"{colors.get(color, colors['white'])}{text}{colors['reset']}")

def log_info(msg: str):
    print_colored(f"ℹ️  {msg}", 'cyan')

def log_success(msg: str):
    print_colored(f"✅ {msg}", 'green')

def log_warning(msg: str):
    print_colored(f"⚠️  {msg}", 'yellow')

def log_error(msg: str):
    print_colored(f"❌ {msg}", 'red')

def log_title(msg: str):
    print_colored(f"\n🔧 {msg}", 'blue')

# ========================================
# 📁 FILE OPERATIONS
# ========================================

def update_api_config_file(environment: str) -> bool:
    """Update api_config.py file with new environment settings"""
    try:
        # Read the current file
        with open('api_config.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        config = URL_CONFIGS[environment]
        
        # Update each configuration value
        for key, value in config.items():
            if key == 'CORS_ORIGINS':
                # Handle list of CORS origins
                origins_str = ',\n                    '.join([f"'{origin}'" for origin in value])
                pattern = f"{key}:\\s*\\[[^\\]]*\\]"
                replacement = f"{key}: [\n                    {origins_str}\n                ]"
            else:
                # Handle simple values
                if isinstance(value, str):
                    pattern = f"{key}:\\s*['\"][^'\"]*['\"]"
                    replacement = f"{key}: '{value}'"
                elif isinstance(value, bool):
                    pattern = f"{key}:\\s*(True|False)"
                    replacement = f"{key}: {value}"
                else:
                    pattern = f"{key}:\\s*\\d+"
                    replacement = f"{key}: {value}"
            
            import re
            content = re.sub(pattern, replacement, content)
        
        # Write back to file
        with open('api_config.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        log_success(f"Updated api_config.py for {environment} environment")
        return True
        
    except Exception as e:
        log_error(f"Error updating api_config.py: {e}")
        return False

def update_environment_variables(env_vars: Dict[str, str]) -> bool:
    """Create or update .env file with environment variables"""
    try:
        env_content = []
        
        # Add environment variables
        for key, value in env_vars.items():
            env_content.append(f"{key}={value}")
        
        # Write to .env file
        with open('.env', 'w', encoding='utf-8') as f:
            f.write('\n'.join(env_content))
        
        log_success("Updated .env file")
        return True
        
    except Exception as e:
        log_error(f"Error updating .env file: {e}")
        return False

# ========================================
# 🎯 MAIN FUNCTIONS
# ========================================

def show_current_config():
    """Show current URL configurations"""
    log_title("Current API URL Configurations")
    
    for env, config in URL_CONFIGS.items():
        print_colored(f"\n{env.upper()}:", 'yellow')
        for key, value in config.items():
            if key == 'CORS_ORIGINS':
                print(f"  {key}: {len(value)} origins")
            else:
                print(f"  {key}: {value}")

def change_environment(environment: str):
    """Change to specific environment"""
    log_title(f"Changing to {environment} environment")
    
    if environment not in URL_CONFIGS:
        log_error(f"Invalid environment: {environment}")
        log_info(f"Available environments: {', '.join(URL_CONFIGS.keys())}")
        return False
    
    # Update api_config.py
    success1 = update_api_config_file(environment)
    
    # Update environment variables
    env_vars = {
        'FLASK_ENV': environment,
        'API_PORT': str(URL_CONFIGS[environment]['PORT']),
        'FRONTEND_URL': URL_CONFIGS[environment]['FRONTEND_URL']
    }
    success2 = update_environment_variables(env_vars)
    
    if success1 and success2:
        log_success(f"Successfully changed to {environment} environment")
        log_info("Updated URLs:")
        for key, value in URL_CONFIGS[environment].items():
            if key != 'CORS_ORIGINS':
                print(f"  {key}: {value}")
        return True
    else:
        log_error("Failed to update some files")
        return False

def set_custom_urls(host: str, port: int, frontend_url: str, debug: bool = False):
    """Set custom URLs"""
    log_title("Setting custom URLs")
    
    custom_config = {
        'HOST': host,
        'PORT': port,
        'DEBUG': debug,
        'FRONTEND_URL': frontend_url,
        'CORS_ORIGINS': [frontend_url]
    }
    
    # Update api_config.py with custom values
    try:
        with open('api_config.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update each configuration value
        for key, value in custom_config.items():
            if key == 'CORS_ORIGINS':
                origins_str = ',\n                    '.join([f"'{origin}'" for origin in value])
                pattern = f"{key}:\\s*\\[[^\\]]*\\]"
                replacement = f"{key}: [\n                    {origins_str}\n                ]"
            else:
                if isinstance(value, str):
                    pattern = f"{key}:\\s*['\"][^'\"]*['\"]"
                    replacement = f"{key}: '{value}'"
                elif isinstance(value, bool):
                    pattern = f"{key}:\\s*(True|False)"
                    replacement = f"{key}: {value}"
                else:
                    pattern = f"{key}:\\s*\\d+"
                    replacement = f"{key}: {value}"
            
            import re
            content = re.sub(pattern, replacement, content)
        
        # Write back to file
        with open('api_config.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        log_success("Updated with custom URLs:")
        for key, value in custom_config.items():
            if key != 'CORS_ORIGINS':
                print(f"  {key}: {value}")
        
        # Update environment variables
        env_vars = {
            'API_HOST': host,
            'API_PORT': str(port),
            'FRONTEND_URL': frontend_url,
            'API_DEBUG': str(debug).lower()
        }
        update_environment_variables(env_vars)
        
        return True
        
    except Exception as e:
        log_error(f"Error updating with custom URLs: {e}")
        return False

def test_configuration():
    """Test the current configuration"""
    log_title("Testing API Configuration")
    
    try:
        # Import and test the configuration
        from api_config import api_config
        
        log_success("Configuration loaded successfully!")
        log_info("Current settings:")
        print(f"  Environment: {api_config.environment}")
        print(f"  Host: {api_config.HOST}")
        print(f"  Port: {api_config.PORT}")
        print(f"  Debug: {api_config.DEBUG}")
        print(f"  Frontend URL: {api_config.FRONTEND_URL}")
        print(f"  CORS Origins: {len(api_config.CORS_ORIGINS)} origins")
        
        return True
        
    except Exception as e:
        log_error(f"Configuration test failed: {e}")
        return False

# ========================================
# 📋 COMMAND LINE INTERFACE
# ========================================

def show_help():
    """Show help information"""
    log_title("API URL Change Script - Help")
    print("""
Usage: python change-api-url.py [command] [options]

Commands:
  show                    Show current URL configurations
  dev                     Change to development environment
  staging                 Change to staging environment
  prod                    Change to production environment
  custom <host> <port> <frontend_url> [debug]  Set custom URLs
  test                    Test current configuration

Examples:
  python change-api-url.py show
  python change-api-url.py dev
  python change-api-url.py prod
  python change-api-url.py custom 0.0.0.0 8000 https://my-domain.com
  python change-api-url.py custom localhost 5001 http://localhost:3000 true

Available environments: """ + ', '.join(URL_CONFIGS.keys()) + """

Environment Variables:
  FLASK_ENV              Set environment (development/staging/production)
  API_HOST               Set API host
  API_PORT               Set API port
  FRONTEND_URL           Set frontend URL
  API_DEBUG              Set debug mode (true/false)
    """)

# ========================================
# 🚀 MAIN EXECUTION
# ========================================

def main():
    args = sys.argv[1:]
    
    if not args or args[0] in ['help', '--help', '-h']:
        show_help()
        return
    
    command = args[0]
    
    try:
        if command == 'show':
            show_current_config()
            
        elif command == 'dev':
            change_environment('development')
            
        elif command == 'staging':
            change_environment('staging')
            
        elif command == 'prod':
            change_environment('production')
            
        elif command == 'custom':
            if len(args) < 4:
                log_error("Custom command requires host, port, and frontend_url")
                show_help()
                return
            
            host = args[1]
            port = int(args[2])
            frontend_url = args[3]
            debug = args[4].lower() == 'true' if len(args) > 4 else False
            
            set_custom_urls(host, port, frontend_url, debug)
            
        elif command == 'test':
            test_configuration()
            
        else:
            log_error(f"Unknown command: {command}")
            show_help()
            
    except KeyboardInterrupt:
        log_warning("\nOperation cancelled by user")
    except Exception as e:
        log_error(f"Error: {e}")

if __name__ == "__main__":
    main() 