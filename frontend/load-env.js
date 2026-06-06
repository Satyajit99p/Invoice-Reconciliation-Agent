/**
 * Load environment variables from root .env file for React app
 * This script ensures frontend can access variables from the root .env file
 */

const fs = require('fs');
const path = require('path');

function loadRootEnv() {
  const rootEnvPath = path.join(__dirname, '..', '.env');
  const frontendEnvPath = path.join(__dirname, '.env.local');

  // Check if root .env exists
  if (!fs.existsSync(rootEnvPath)) {
    console.log('No root .env file found, skipping environment setup');
    return;
  }

  try {
    // Read root .env file
    const rootEnvContent = fs.readFileSync(rootEnvPath, 'utf8');
    
    // Filter only REACT_APP_ variables and other frontend-relevant ones
    const frontendVars = rootEnvContent
      .split('\n')
      .filter(line => {
        const trimmed = line.trim();
        // Only include valid lines that are not comments
        if (!trimmed || trimmed.startsWith('#')) {
          return false;
        }
        
        // Only include specific frontend variables
        const validPrefixes = [
          'REACT_APP_',
          'GENERATE_SOURCEMAP=',
          'BROWSER='
        ];
        
        return validPrefixes.some(prefix => trimmed.startsWith(prefix));
      })
      .map(line => {
        // Ensure no empty values that could cause webpack issues
        const [key, value] = line.split('=');
        if (!value || value.trim() === '') {
          console.warn(`⚠️  Skipping empty environment variable: ${key}`);
          return null;
        }
        return line;
      })
      .filter(line => line !== null)
      .join('\n');

    // Write to frontend .env.local (which takes precedence)
    if (frontendVars) {
      fs.writeFileSync(frontendEnvPath, frontendVars + '\n');
      console.log('✅ Loaded environment variables from root .env for frontend');
    }
  } catch (error) {
    console.warn('⚠️ Failed to load root .env file:', error.message);
  }
}

// Run if called directly
if (require.main === module) {
  loadRootEnv();
}

module.exports = { loadRootEnv };