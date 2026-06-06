"""
FastAPI application for Invoice Chat Interface.
Integrates with existing chat_agent.py and Supabase database.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api import chat, files, models
from app.core.websocket_manager import ConnectionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global WebSocket connection manager
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Invoice Chat Interface API")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"CORS Origins: {settings.CORS_ORIGINS}")
    
    # Test database connection
    try:
        from data.supabase_chat import chat_db
        # Try a simple query to test connection
        chat_db.list_active_sessions(limit=1)
        logger.info("✅ Supabase connection established")
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {e}")
        
    # Test Ollama connection  
    try:
        import ollama
        ollama.list()
        logger.info("✅ Ollama connection established")
    except Exception as e:
        logger.warning(f"⚠️ Ollama connection failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Invoice Chat Interface API")
    # Cleanup active WebSocket connections
    await manager.disconnect_all()


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Invoice Chat Interface API",
        description="Chat interface for invoice reconciliation with file upload and multi-model support",
        version="1.0.0",
        docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
        lifespan=lifespan
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Include API routers
    app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
    app.include_router(files.router, prefix="/api/v1", tags=["files"])
    app.include_router(models.router, prefix="/api/v1", tags=["models"])

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "version": "1.0.0"
        }

    # WebSocket endpoint for real-time chat updates
    @app.websocket("/ws/chat/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        """WebSocket endpoint for real-time chat updates."""
        await manager.connect(websocket, session_id)
        try:
            while True:
                # Keep connection alive and handle any incoming messages
                data = await websocket.receive_text()
                # Echo back for connection testing (can be removed in production)
                await manager.send_personal_message(f"Echo: {data}", session_id)
        except WebSocketDisconnect:
            await manager.disconnect(websocket, session_id)
        except Exception as e:
            logger.error(f"WebSocket error for session {session_id}: {e}")
            await manager.disconnect(websocket, session_id)

    # Serve static files for uploaded content (with security considerations)
    if os.path.exists("uploads"):
        app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

    # Basic frontend for development (optional)
    if settings.ENVIRONMENT == "development":
        @app.get("/", response_class=HTMLResponse)
        async def development_frontend():
            """Simple development frontend."""
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Invoice Chat Interface - Dev</title>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                    .info { background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }
                </style>
            </head>
            <body>
                <h1>Invoice Chat Interface API</h1>
                <div class="info">
                    <h3>Development Mode</h3>
                    <p>API is running in development mode.</p>
                    <ul>
                        <li><a href="/docs">API Documentation (Swagger)</a></li>
                        <li><a href="/redoc">API Documentation (ReDoc)</a></li>
                        <li><a href="/health">Health Check</a></li>
                    </ul>
                </div>
                <div class="info">
                    <h3>WebSocket Testing</h3>
                    <p>WebSocket endpoint: <code>ws://localhost:8000/ws/chat/{session_id}</code></p>
                </div>
                <div class="info">
                    <h3>Frontend Development</h3>
                    <p>The React frontend should be served separately during development.</p>
                    <p>Make sure to configure CORS origins in the environment variables.</p>
                </div>
            </body>
            </html>
            """

    return app


# Create the FastAPI app instance
app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )