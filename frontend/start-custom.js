const { spawn } = require('child_process');
const path = require('path');

// Custom start script that bypasses the allowedHosts validation issue
console.log('🚀 Starting React development server with custom configuration...');

// Set environment variables to prevent the allowedHosts issue
process.env.SKIP_PREFLIGHT_CHECK = 'true';
process.env.HOST = 'localhost';
process.env.PORT = '3000';
process.env.BROWSER = 'none'; // Don't auto-open browser to avoid issues
process.env.NODE_OPTIONS = '--openssl-legacy-provider'; // Fix for Node.js v17+ compatibility

// Start react-scripts with modified environment
const reactScripts = spawn('npx', ['react-scripts', 'start'], {
  stdio: 'inherit',
  shell: true,
  env: {
    ...process.env,
    // Override problematic configurations
    WDS_SOCKET_HOST: 'localhost',
    WDS_SOCKET_PORT: '3000',
    GENERATE_SOURCEMAP: 'false', // Disable source maps to reduce complexity
    DANGEROUSLY_DISABLE_HOST_CHECK: 'true',
  }
});

reactScripts.on('close', (code) => {
  console.log(`React Scripts exited with code ${code}`);
  process.exit(code);
});

reactScripts.on('error', (err) => {
  console.error('Failed to start React Scripts:', err);
  process.exit(1);
});