"""
WebSocket connection manager for real-time chat updates.
Handles multiple clients per chat session.
"""

import json
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for chat sessions."""
    
    def __init__(self):
        # Dictionary mapping session_id to list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Connect a client to a chat session."""
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        
        self.active_connections[session_id].append(websocket)
        logger.info(f"Client connected to session {session_id}. Total connections: {len(self.active_connections[session_id])}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "message": "Connected to chat session",
            "session_id": session_id
        }, session_id)
    
    async def disconnect(self, websocket: WebSocket, session_id: str):
        """Disconnect a client from a chat session."""
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
                logger.info(f"Client disconnected from session {session_id}. Remaining connections: {len(self.active_connections[session_id])}")
            
            # Remove session if no connections left
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
                logger.info(f"Session {session_id} removed (no active connections)")
    
    async def send_personal_message(self, message, session_id: str):
        """Send message to all clients in a specific session."""
        if session_id not in self.active_connections:
            return
        
        # Ensure message is JSON serializable
        if isinstance(message, str):
            message_data = {"type": "message", "content": message}
        else:
            message_data = message
        
        message_json = json.dumps(message_data)
        
        # Send to all connections in the session
        disconnected = []
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send message to client in session {session_id}: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            await self.disconnect(connection, session_id)
    
    async def broadcast_to_session(self, session_id: str, message_type: str, data: dict):
        """Broadcast a structured message to all clients in a session."""
        message = {
            "type": message_type,
            "timestamp": json.dumps(None),  # Will be set by JSON encoder
            "session_id": session_id,
            **data
        }
        
        # Add timestamp
        import datetime
        message["timestamp"] = datetime.datetime.utcnow().isoformat()
        
        await self.send_personal_message(message, session_id)
    
    async def send_process_step(self, session_id: str, step: str, status: str = "in_progress", details: dict = None):
        """Send process step update to clients."""
        await self.broadcast_to_session(session_id, "process_step", {
            "step": step,
            "status": status,  # "starting", "in_progress", "completed", "failed"
            "details": details or {}
        })
    
    async def send_tool_execution(self, session_id: str, tool_name: str, status: str, result: dict = None, error: str = None):
        """Send tool execution update to clients."""
        await self.broadcast_to_session(session_id, "tool_execution", {
            "tool_name": tool_name,
            "status": status,  # "starting", "completed", "failed"
            "result": result,
            "error": error
        })
    
    async def send_model_update(self, session_id: str, model_name: str, status: str = "active"):
        """Send model change notification to clients."""
        await self.broadcast_to_session(session_id, "model_update", {
            "model_name": model_name,
            "status": status
        })
    
    async def send_file_update(self, session_id: str, filename: str, status: str, progress: float = None, error: str = None):
        """Send file upload/processing update to clients."""
        await self.broadcast_to_session(session_id, "file_update", {
            "filename": filename,
            "status": status,  # "uploading", "processing", "completed", "failed"
            "progress": progress,
            "error": error
        })
    
    async def send_error(self, session_id: str, error_message: str, error_code: str = None):
        """Send error message to clients."""
        await self.broadcast_to_session(session_id, "error", {
            "message": error_message,
            "code": error_code or "general_error"
        })
    
    async def disconnect_all(self):
        """Disconnect all active connections (for shutdown)."""
        for session_id, connections in self.active_connections.items():
            for connection in connections[:]:  # Create a copy to avoid modification during iteration
                try:
                    await connection.close()
                except Exception as e:
                    logger.warning(f"Error closing connection for session {session_id}: {e}")
        
        self.active_connections.clear()
        logger.info("All WebSocket connections disconnected")
    
    def get_session_count(self) -> int:
        """Get number of active sessions."""
        return len(self.active_connections)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_session_info(self) -> Dict[str, int]:
        """Get information about active sessions."""
        return {
            session_id: len(connections) 
            for session_id, connections in self.active_connections.items()
        }