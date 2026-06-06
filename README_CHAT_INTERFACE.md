# Invoice Chat Interface

A modern React-based chat interface for the Invoice Reconciliation Agent, featuring file uploads, multi-model support, and real-time process visualization.

## 🚀 Features

- **Modern Chat Interface**: Clean, responsive UI with message bubbles and real-time updates
- **File Upload Support**: Drag-and-drop Excel, CSV, and PDF files with processing status
- **Multi-Model Support**: Switch between Ollama (local) and cloud API models (OpenAI, Anthropic)
- **Process Visualization**: Real-time step-by-step processing indicators
- **Session Management**: Persistent chat sessions with conversation history
- **Error Handling**: Comprehensive error handling with user-friendly fallback messages
- **WebSocket Integration**: Real-time updates for processing steps and file status

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend│    │  FastAPI Backend│    │ Supabase PostgreSQL│
│                 │    │                 │    │                 │
│ • Chat Interface│◄───┤ • REST API      │◄───┤ • Chat Sessions │
│ • File Upload   │    │ • WebSocket     │    │ • Messages      │
│ • Model Select  │    │ • File Handling │    │ • Files         │
│ • Process View  │    │ • Session Mgmt  │    │ • Metadata      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  Existing Agent │
                       │                 │
                       │ • chat_agent.py │
                       │ • Tool Registry │
                       │ • Semantic Match│
                       └─────────────────┘
```

## 📋 Prerequisites

1. **Database Setup**: Execute the SQL migration to create chat tables
2. **Supabase Configuration**: Ensure existing Supabase environment variables are set
3. **Ollama Setup** (optional): Install Ollama and pull models
4. **Node.js**: Version 16+ for the React frontend
5. **Python**: Version 3.8+ for the FastAPI backend

## 🛠️ Installation & Setup

### 1. Database Migration

Execute the SQL migration in your Supabase dashboard:

```bash
# In Supabase SQL Editor, run:
backend/migrations/001_chat_schema.sql
```

### 2. Backend Setup

```bash
# Copy and configure the unified environment file (from project root)
cp .env.example .env
# Edit .env with your configuration

cd backend

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server
python start_server.py
```

The backend will be available at `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend

# Install Node.js dependencies
npm install

# Start the React development server (automatically loads env from root)
npm start
```

**Note**: The frontend uses a custom start script that resolves Node.js v17+ compatibility issues and webpack dev server validation problems. If you encounter any startup issues, you can also try:
- `npm run start-original` - Uses the standard react-scripts start
- `node start-custom.js` - Direct custom script execution

The frontend will be available at `http://localhost:3000`

## 🔧 Configuration

### Unified Environment Configuration (.env)

The chat interface uses a single `.env` file at the project root that serves both backend and frontend:

```bash
# Existing Supabase Configuration (keep your values)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_DB_HOST=your_db_host
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=your_db_name
SUPABASE_DB_USER=your_db_user
SUPABASE_DB_PASSWORD=your_db_password

# Chat Interface Configuration
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000

# Frontend API Configuration
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_WS_URL=ws://localhost:8000

# File Upload Settings
MAX_FILE_SIZE=10485760  # 10MB
UPLOAD_DIR=uploads

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3.2

# Cloud APIs (optional)
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Model Configuration
DEFAULT_MODEL=llama3.2
ENABLE_CLOUD_MODELS=false
MODEL_FALLBACK_ENABLED=true
```

**Note**: The frontend automatically loads `REACT_APP_*` variables from the root `.env` file during build/start.

## 📊 Database Schema

The chat interface adds these tables to your existing Supabase database:

- **chat_sessions**: Chat session management with expiration and model preferences
- **chat_messages**: Message storage with metadata for tool calls and processing info
- **session_files**: File upload tracking with processing status

## 🔌 API Endpoints

### Chat API
- `POST /api/v1/chat/sessions` - Create new session
- `POST /api/v1/chat/sessions/{id}/messages` - Send message
- `GET /api/v1/chat/sessions/{id}/messages` - Get message history
- `GET /api/v1/chat/sessions/{id}/conversation` - Get full conversation

### File API
- `POST /api/v1/files/upload/{session_id}` - Upload file
- `GET /api/v1/files/{session_id}` - List session files
- `GET /api/v1/files/{session_id}/{file_id}/download` - Download file

### Model API
- `GET /api/v1/models` - List available models
- `POST /api/v1/models/select/{session_id}` - Change session model

### WebSocket
- `ws://localhost:8000/ws/chat/{session_id}` - Real-time updates

## 🎯 Usage

1. **Start a Chat**: The interface automatically creates a session on load
2. **Upload Files**: Drag and drop Excel, CSV, or PDF files for analysis
3. **Ask Questions**: Type messages about invoice reconciliation, data analysis, etc.
4. **Switch Models**: Use the model selector to change between available models
5. **Monitor Progress**: Watch real-time processing steps for each request

## 🔍 Features in Detail

### File Upload
- Supports Excel (.xlsx, .xls), CSV (.csv), and PDF files
- Drag-and-drop interface with progress tracking
- File validation and size limits (10MB default)
- Processing status indicators (pending → processing → completed/failed)

### Model Selection
- Automatic detection of available Ollama models
- Cloud API integration (OpenAI, Anthropic) when configured
- Health status indicators for each provider
- Session-specific model preferences

### Process Visualization
- Step-by-step processing indicators
- Real-time status updates via WebSocket
- Processing time tracking
- Error handling with detailed feedback

### Message Types
- **User Messages**: Your questions and requests
- **Assistant Messages**: AI responses with tool execution details
- **System Messages**: Status updates and notifications

## 🛡️ Error Handling

The interface provides comprehensive error handling:

- **Network Errors**: Automatic retry with user feedback
- **File Upload Errors**: Validation and size limit enforcement
- **Model Errors**: Fallback to available models
- **Processing Errors**: User-friendly error messages
- **WebSocket Reconnection**: Automatic reconnection with exponential backoff

## 🔧 Development

### Project Structure

```
backend/
├── app/
│   ├── api/          # FastAPI route handlers
│   ├── core/         # Configuration and utilities
│   ├── models/       # Pydantic models
│   └── services/     # Business logic
├── migrations/       # Database migrations
└── start_server.py   # Development server

frontend/
├── src/
│   ├── components/   # React components
│   ├── hooks/        # Custom hooks
│   └── services/     # API client
└── public/          # Static assets
```

### Adding New Features

1. **Backend**: Add routes in `app/api/`, business logic in `app/services/`
2. **Frontend**: Create components in `src/components/`, add API calls in `src/services/api.js`
3. **Database**: Add migrations to `migrations/`

## 🚀 Deployment

### Production Setup

1. **Backend**: Use a production WSGI server like Gunicorn
2. **Frontend**: Build with `npm run build` and serve with nginx
3. **Database**: Use Supabase production instance
4. **Environment**: Set production environment variables

### Docker Deployment (Optional)

Create Dockerfiles for both backend and frontend, or use docker-compose for the full stack.

## 🤝 Integration with Existing Agent

The chat interface seamlessly integrates with your existing `agent/chat_agent.py`:

- Uses the same tool registry and semantic matching
- Leverages existing Supabase database and environment configuration
- Wraps the existing `process_user_intent()` function with enhanced features
- Maintains compatibility with existing invoice reconciliation workflows

## 📈 Monitoring

- **Health Checks**: `/health` endpoint for service monitoring
- **Logs**: Comprehensive logging for debugging and monitoring
- **WebSocket Status**: Real-time connection status indicators
- **File Processing**: Upload and processing status tracking

## 🔐 Security Considerations

- File upload validation and size limits
- Session-based file isolation
- Input sanitization for chat messages
- CORS configuration for frontend access
- Row Level Security (RLS) enabled on database tables

## 📝 License

This chat interface extends the existing Invoice Reconciliation Agent project and follows the same license terms.