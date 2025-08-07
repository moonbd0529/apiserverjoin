#!/usr/bin/env node

// 🔗 URL Change Script
// সহজে URL পরিবর্তন করার জন্য

const fs = require('fs');
const path = require('path');

// ========================================
// 🌐 URL CONFIGURATIONS
// ========================================
const URL_CONFIGS = {
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

// ========================================
// 🔧 HELPER FUNCTIONS
// ========================================

// Color output functions
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m'
};

const log = {
  info: (msg) => console.log(`${colors.cyan}ℹ️  ${msg}${colors.reset}`),
  success: (msg) => console.log(`${colors.green}✅ ${msg}${colors.reset}`),
  warning: (msg) => console.log(`${colors.yellow}⚠️  ${msg}${colors.reset}`),
  error: (msg) => console.log(`${colors.red}❌ ${msg}${colors.reset}`),
  title: (msg) => console.log(`${colors.bright}${colors.blue}${msg}${colors.reset}`)
};

// ========================================
// 📁 FILE OPERATIONS
// ========================================

// Update environment.js file
function updateEnvironmentFile(environment) {
  const filePath = path.join(__dirname, 'admin', 'src', 'environment.js');
  
  if (!fs.existsSync(filePath)) {
    log.error(`File not found: ${filePath}`);
    return false;
  }
  
  try {
    let content = fs.readFileSync(filePath, 'utf8');
    const config = URL_CONFIGS[environment];
    
    if (!config) {
      log.error(`Invalid environment: ${environment}`);
      return false;
    }
    
    // Update URLs in the file
    Object.keys(config).forEach(key => {
      const regex = new RegExp(`${key}:\\s*['"][^'"]*['"]`, 'g');
      const replacement = `${key}: '${config[key]}'`;
      content = content.replace(regex, replacement);
    });
    
    fs.writeFileSync(filePath, content, 'utf8');
    log.success(`Updated ${filePath} for ${environment} environment`);
    return true;
  } catch (error) {
    log.error(`Error updating file: ${error.message}`);
    return false;
  }
}

// Update config.js file
function updateConfigFile() {
  const filePath = path.join(__dirname, 'admin', 'src', 'config.js');
  
  if (!fs.existsSync(filePath)) {
    log.error(`File not found: ${filePath}`);
    return false;
  }
  
  try {
    let content = fs.readFileSync(filePath, 'utf8');
    
    // Update BASE_URL reference
    const baseUrlRegex = /const BASE_URL = [^;]+;/;
    const newBaseUrl = "const BASE_URL = environmentConfig.API_BASE_URL;";
    content = content.replace(baseUrlRegex, newBaseUrl);
    
    fs.writeFileSync(filePath, content, 'utf8');
    log.success(`Updated ${filePath}`);
    return true;
  } catch (error) {
    log.error(`Error updating config file: ${error.message}`);
    return false;
  }
}

// ========================================
// 🎯 MAIN FUNCTIONS
// ========================================

// Show current configuration
function showCurrentConfig() {
  log.title('Current URL Configuration');
  
  Object.keys(URL_CONFIGS).forEach(env => {
    log.info(`${env.toUpperCase()}:`);
    Object.entries(URL_CONFIGS[env]).forEach(([key, value]) => {
      console.log(`  ${key}: ${value}`);
    });
    console.log('');
  });
}

// Change to specific environment
function changeEnvironment(environment) {
  log.title(`Changing to ${environment} environment`);
  
  if (!URL_CONFIGS[environment]) {
    log.error(`Invalid environment: ${environment}`);
    log.info('Available environments: ' + Object.keys(URL_CONFIGS).join(', '));
    return false;
  }
  
  const success1 = updateEnvironmentFile(environment);
  const success2 = updateConfigFile();
  
  if (success1 && success2) {
    log.success(`Successfully changed to ${environment} environment`);
    log.info('URLs updated:');
    Object.entries(URL_CONFIGS[environment]).forEach(([key, value]) => {
      console.log(`  ${key}: ${value}`);
    });
    return true;
  } else {
    log.error('Failed to update some files');
    return false;
  }
}

// Set custom URLs
function setCustomUrls(apiUrl, socketUrl, mediaUrl, frontendUrl) {
  log.title('Setting custom URLs');
  
  const customConfig = {
    API_BASE_URL: apiUrl,
    SOCKET_URL: socketUrl || apiUrl,
    MEDIA_BASE_URL: mediaUrl || `${apiUrl}/media`,
    FRONTEND_URL: frontendUrl || apiUrl.replace(':5001', ':3000')
  };
  
  // Update environment.js with custom URLs
  const filePath = path.join(__dirname, 'admin', 'src', 'environment.js');
  
  try {
    let content = fs.readFileSync(filePath, 'utf8');
    
    // Update development URLs with custom values
    Object.keys(customConfig).forEach(key => {
      const regex = new RegExp(`${key}:\\s*['"][^'"]*['"]`, 'g');
      const replacement = `${key}: '${customConfig[key]}'`;
      content = content.replace(regex, replacement);
    });
    
    fs.writeFileSync(filePath, content, 'utf8');
    log.success('Updated with custom URLs:');
    Object.entries(customConfig).forEach(([key, value]) => {
      console.log(`  ${key}: ${value}`);
    });
    return true;
  } catch (error) {
    log.error(`Error updating file: ${error.message}`);
    return false;
  }
}

// ========================================
// 📋 COMMAND LINE INTERFACE
// ========================================

function showHelp() {
  log.title('URL Change Script - Help');
  console.log(`
Usage: node change-url.js [command] [options]

Commands:
  show                    Show current URL configurations
  dev                     Change to development environment
  staging                 Change to staging environment
  prod                    Change to production environment
  custom <api> [socket] [media] [frontend]  Set custom URLs

Examples:
  node change-url.js show
  node change-url.js dev
  node change-url.js prod
  node change-url.js custom https://my-domain.com
  node change-url.js custom http://localhost:8000 http://localhost:8000 http://localhost:8000/media http://localhost:3000

Available environments: ${Object.keys(URL_CONFIGS).join(', ')}
  `);
}

// ========================================
// 🚀 MAIN EXECUTION
// ========================================

function main() {
  const args = process.argv.slice(2);
  const command = args[0];
  
  if (!command || command === 'help' || command === '--help' || command === '-h') {
    showHelp();
    return;
  }
  
  switch (command) {
    case 'show':
      showCurrentConfig();
      break;
      
    case 'dev':
    case 'development':
      changeEnvironment('development');
      break;
      
    case 'staging':
      changeEnvironment('staging');
      break;
      
    case 'prod':
    case 'production':
      changeEnvironment('production');
      break;
      
    case 'custom':
      const apiUrl = args[1];
      const socketUrl = args[2];
      const mediaUrl = args[3];
      const frontendUrl = args[4];
      
      if (!apiUrl) {
        log.error('API URL is required for custom configuration');
        showHelp();
        return;
      }
      
      setCustomUrls(apiUrl, socketUrl, mediaUrl, frontendUrl);
      break;
      
    default:
      log.error(`Unknown command: ${command}`);
      showHelp();
      break;
  }
}

// Run the script
if (require.main === module) {
  main();
}

module.exports = {
  changeEnvironment,
  setCustomUrls,
  showCurrentConfig,
  URL_CONFIGS
}; 