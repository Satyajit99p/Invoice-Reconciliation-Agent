#!/usr/bin/env python3
"""
Setup script for Invoice Chat Interface.
Run this script to set up the chat interface after implementing the code.
"""

import os
import sys
import subprocess
from pathlib import Path

def print_banner():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                 Invoice Chat Interface Setup                 ║
    ║                                                              ║
    ║  This script will help you set up the chat interface for    ║
    ║  your Invoice Reconciliation Agent.                          ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

def check_requirements():
    """Check if required tools are available."""
    print("\n📋 Checking requirements...")
    
    requirements = {
        "python": "Python 3.8+",
        "node": "Node.js 16+", 
        "npm": "npm package manager"
    }
    
    missing = []
    
    for tool, description in requirements.items():
        try:
            result = subprocess.run([tool, "--version"], 
                                  capture_output=True, text=True, check=True)
            print(f"  ✅ {description}: Found")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"  ❌ {description}: Not found")
            missing.append(tool)
    
    if missing:
        print(f"\n⚠️  Missing requirements: {', '.join(missing)}")
        print("Please install the missing tools before continuing.")
        return False
    
    print("✅ All requirements satisfied!")
    return True

def setup_environment():
    """Set up the unified environment file."""
    print("\n⚙️  Setting up environment configuration...")
    
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists():
        if env_example.exists():
            print("Creating .env file from example...")
            with open(env_example) as f:
                content = f.read()
            with open(env_file, 'w') as f:
                f.write(content)
            print(f"  ✅ Created {env_file}")
            print(f"  ⚠️  Please edit {env_file} with your configuration")
            print(f"  📝 Pay special attention to your existing Supabase settings")
            
            response = input("\n✅ Have you configured the .env file? (y/n): ")
            return response.lower().startswith('y')
        else:
            print(f"  ❌ {env_example} not found")
            return False
    else:
        print("  ✅ .env file already exists")
        return True

def setup_database():
    """Instructions for database setup."""
    print("\n🗄️  Database Setup Required")
    print("=" * 50)
    print("""
    1. Open your Supabase dashboard
    2. Go to the SQL Editor
    3. Run the migration file: migrations/001_chat_schema.sql
    
    This will create the following tables:
    • chat_sessions (session management)
    • chat_messages (conversation history) 
    • session_files (file uploads)
    
    Make sure your .env file contains your Supabase settings:
    • SUPABASE_URL
    • SUPABASE_KEY
    • SUPABASE_DB_* (connection parameters)
    """)
    
    response = input("\n✅ Have you completed the database setup? (y/n): ")
    return response.lower().startswith('y')

def setup_backend():
    """Set up the FastAPI backend."""
    print("\n🔧 Setting up FastAPI backend...")
    
    backend_dir = Path("backend")
    
    # Install Python dependencies
    print("Installing Python dependencies...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", 
            str(backend_dir / "requirements.txt")
        ], check=True)
        print("  ✅ Python dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed to install Python dependencies: {e}")
        return False
    
    return True

def setup_frontend():
    """Set up the React frontend."""
    print("\n⚛️  Setting up React frontend...")
    
    frontend_dir = Path("frontend")
    
    # Install Node.js dependencies
    print("Installing Node.js dependencies...")
    try:
        subprocess.run(["npm", "install"], 
                      cwd=frontend_dir, check=True)
        print("  ✅ Node.js dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed to install Node.js dependencies: {e}")
        return False
    
    return True

def check_ollama():
    """Check Ollama setup."""
    print("\n🦙 Checking Ollama setup...")
    
    try:
        result = subprocess.run(["ollama", "list"], 
                              capture_output=True, text=True, check=True)
        print("  ✅ Ollama is running")
        
        # Check for llama3.2 model
        if "llama3.2" in result.stdout:
            print("  ✅ llama3.2 model found")
        else:
            print("  ⚠️  llama3.2 model not found")
            response = input("    Do you want to pull llama3.2? (y/n): ")
            if response.lower().startswith('y'):
                print("    Pulling llama3.2 model...")
                subprocess.run(["ollama", "pull", "llama3.2"], check=True)
                print("    ✅ llama3.2 model pulled")
        
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  ⚠️  Ollama not found or not running")
        print("     The chat interface will work without Ollama if you configure cloud APIs")
        return True

def print_next_steps():
    """Print next steps for the user."""
    print("""
    🎉 Setup Complete!
    
    Next Steps:
    ═══════════
    
    1. Start the Backend Server:
       cd backend
       python start_server.py
       
       Backend will be available at: http://localhost:8000
       API docs: http://localhost:8000/docs
    
    2. Start the Frontend (in a new terminal):
       cd frontend
       npm start
       
       Frontend will be available at: http://localhost:3000
    
    3. Optional - Cloud API Models:
       • Add OPENAI_API_KEY to root .env file for OpenAI models
       • Add ANTHROPIC_API_KEY to root .env file for Anthropic models
    
    4. Test the Interface:
       • Upload Excel/CSV/PDF files
       • Ask questions about invoice reconciliation
       • Switch between available models
    
    📚 Documentation:
       • See README_CHAT_INTERFACE.md for detailed information
       • Check backend/migrations/001_chat_schema.sql for database schema
    
    🎯 Features Available:
       ✅ Modern chat interface with message history
       ✅ File upload with drag-and-drop (Excel, CSV, PDF)
       ✅ Multi-model support (Ollama + Cloud APIs)
       ✅ Real-time process step visualization
       ✅ Session management with conversation persistence
       ✅ Comprehensive error handling
    
    Happy chatting! 🚀
    """)

def main():
    """Main setup function."""
    print_banner()
    
    if not check_requirements():
        sys.exit(1)
    
    if not setup_environment():
        print("\n❌ Environment configuration is required to continue.")
        sys.exit(1)
    
    if not setup_database():
        print("\n❌ Database setup is required to continue.")
        sys.exit(1)
    
    if not setup_backend():
        print("\n❌ Backend setup failed.")
        sys.exit(1)
    
    if not setup_frontend():
        print("\n❌ Frontend setup failed.")
        sys.exit(1)
    
    check_ollama()
    
    print_next_steps()

if __name__ == "__main__":
    main()