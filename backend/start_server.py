"""
Development server startup script for Invoice Chat Interface.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add parent directory to Python path so we can import from the main project
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Add current directory to path for app imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """Start the development server."""
    
    # Load environment variables from root .env file if it exists
    root_env_file = parent_dir / ".env"
    backend_env_file = current_dir / ".env"
    
    if root_env_file.exists():
        print(f"Loading environment from {root_env_file}")
        from dotenv import load_dotenv
        load_dotenv(root_env_file)
    elif backend_env_file.exists():
        print(f"Loading environment from {backend_env_file}")
        from dotenv import load_dotenv
        load_dotenv(backend_env_file)
    else:
        print("No .env file found. Using environment variables or defaults.")
    
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    environment = os.getenv("ENVIRONMENT", "development")
    
    print(f"""
🚀 Starting Invoice Chat Interface API Server
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Environment: {environment}
Host: {host}
Port: {port}
Docs: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/docs
Health: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/health
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Make sure you have:
✓ Supabase environment variables set
✓ Ollama running with llama3.2 model (optional)
✓ Database schema migrated (see migrations/001_chat_schema.sql)

Starting server...
""")
    
    # Start server
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=environment == "development",
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()