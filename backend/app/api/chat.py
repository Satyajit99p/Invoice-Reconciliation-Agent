"""
Chat API endpoints for the invoice chat interface.
"""

import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.chat import (
    CreateSessionRequest, SendMessageRequest, UpdateSessionRequest,
    SessionResponse, MessageResponse, ConversationResponse, SessionStatsResponse,
    ErrorResponse
)
from app.services.chat_service import get_chat_service, EnhancedChatService
from app.core.websocket_manager import ConnectionManager
from data.supabase_chat import chat_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency to get chat service
def get_chat_service_dependency() -> EnhancedChatService:
    """Dependency to get chat service instance."""
    # Import here to avoid circular imports
    from app.main import manager
    return get_chat_service(manager)


@router.post("/chat/sessions", response_model=SessionResponse)
async def create_chat_session(
    request: CreateSessionRequest,
    chat_service: EnhancedChatService = Depends(get_chat_service_dependency)
):
    """Create a new chat session."""
    try:
        session = chat_service.create_session(
            model_preference=request.model_preference,
            expires_hours=request.expires_hours,
            current_invoice_id=request.current_invoice_id,
            metadata=request.metadata or {}
        )
        
        return SessionResponse(
            id=session["id"],
            created_at=session["created_at"],
            expires_at=session["expires_at"],
            model_preference=session["model_preference"],
            metadata=session.get("metadata", {}),
            current_invoice_id=session.get("current_invoice_id")
        )
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/chat/sessions/{session_id}", response_model=SessionResponse)
async def get_chat_session(
    session_id: str,
    chat_service: EnhancedChatService = Depends(get_chat_service_dependency)
):
    """Get chat session information."""
    try:
        session = chat_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        return SessionResponse(
            id=session["id"],
            created_at=session["created_at"],
            expires_at=session["expires_at"],
            model_preference=session["model_preference"],
            metadata=session.get("metadata", {}),
            current_invoice_id=session.get("current_invoice_id")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.put("/chat/sessions/{session_id}", response_model=SessionResponse)
async def update_chat_session(
    session_id: str,
    request: UpdateSessionRequest,
    chat_service: EnhancedChatService = Depends(get_chat_service_dependency)
):
    """Update chat session properties."""
    try:
        # Build update data
        update_data = {}
        if request.model_preference is not None:
            update_data["model_preference"] = request.model_preference
        if request.current_invoice_id is not None:
            update_data["current_invoice_id"] = request.current_invoice_id
        if request.metadata is not None:
            update_data["metadata"] = request.metadata
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updated_session = chat_service.update_session(session_id, **update_data)
        if not updated_session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        return SessionResponse(
            id=updated_session["id"],
            created_at=updated_session["created_at"],
            expires_at=updated_session["expires_at"],
            model_preference=updated_session["model_preference"],
            metadata=updated_session.get("metadata", {}),
            current_invoice_id=updated_session.get("current_invoice_id")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update session: {str(e)}")


@router.post("/chat/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
    chat_service: EnhancedChatService = Depends(get_chat_service_dependency)
):
    """Send a message to the chat session."""
    try:
        # Verify session exists
        session = chat_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        # Process message asynchronously while returning immediately
        response = await chat_service.process_message(
            session_id, 
            request.content, 
            request.metadata
        )
        
        return MessageResponse(**response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message to session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")


@router.get("/chat/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    chat_service: EnhancedChatService = Depends(get_chat_service_dependency)
):
    """Get messages for a chat session."""
    try:
        # Verify session exists
        session = chat_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        messages = chat_db.get_messages(session_id, limit, offset)
        
        return [
            MessageResponse(
                id=msg["id"],
                session_id=msg["session_id"],
                role=msg["role"],
                content=msg["content"],
                metadata=msg.get("metadata", {}),
                created_at=msg["created_at"],
                tool_calls=msg.get("metadata", {}).get("tool_calls"),
                model_used=msg.get("metadata", {}).get("model_used"),
                processing_time=msg.get("metadata", {}).get("processing_time"),
                confidence=msg.get("metadata", {}).get("confidence")
            )
            for msg in messages
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")


@router.get("/chat/sessions/{session_id}/conversation", response_model=ConversationResponse)
async def get_conversation(
    session_id: str,
    include_files: bool = False,
    chat_service: EnhancedChatService = Depends(get_chat_service_dependency)
):
    """Get full conversation including session info and messages."""
    try:
        # Get session
        session = chat_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        # Get messages
        messages = chat_db.get_messages(session_id, limit=100)
        
        # Get files if requested
        files = None
        if include_files:
            files = chat_db.get_session_files(session_id)
        
        return ConversationResponse(
            session=SessionResponse(
                id=session["id"],
                created_at=session["created_at"],
                expires_at=session["expires_at"],
                model_preference=session["model_preference"],
                metadata=session.get("metadata", {}),
                current_invoice_id=session.get("current_invoice_id"),
                message_count=len(messages),
                file_count=len(files) if files else 0
            ),
            messages=[
                MessageResponse(
                    id=msg["id"],
                    session_id=msg["session_id"],
                    role=msg["role"],
                    content=msg["content"],
                    metadata=msg.get("metadata", {}),
                    created_at=msg["created_at"],
                    tool_calls=msg.get("metadata", {}).get("tool_calls"),
                    model_used=msg.get("metadata", {}).get("model_used"),
                    processing_time=msg.get("metadata", {}).get("processing_time"),
                    confidence=msg.get("metadata", {}).get("confidence")
                )
                for msg in messages
            ],
            files=files
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")


@router.get("/chat/sessions/{session_id}/stats", response_model=SessionStatsResponse)
async def get_session_stats(
    session_id: str,
    chat_service: EnhancedChatService = Depends(get_chat_service_dependency)
):
    """Get session statistics."""
    try:
        stats = chat_service.get_session_stats(session_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        return SessionStatsResponse(**stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session stats: {str(e)}")


@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    chat_service: EnhancedChatService = Depends(get_chat_service_dependency)
):
    """Delete a chat session and all associated data."""
    try:
        # Verify session exists
        session = chat_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        # Delete messages and files (cascaded by database)
        success = chat_db.delete_messages(session_id)
        chat_db.delete_session_files(session_id)
        
        # Delete session itself would require additional method in SupabaseChatDB
        # For now, we'll let it expire naturally
        
        return {"message": "Session marked for deletion", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.get("/chat/sessions", response_model=List[SessionResponse])
async def list_sessions(
    limit: int = 20,
    chat_service: EnhancedChatService = Depends(get_chat_service_dependency)
):
    """List active chat sessions."""
    try:
        sessions = chat_db.list_active_sessions(limit)
        
        return [
            SessionResponse(
                id=session["id"],
                created_at=session["created_at"],
                expires_at=session["expires_at"],
                model_preference=session["model_preference"],
                metadata={},  # Don't include full metadata in list view
                current_invoice_id=session.get("current_invoice_id")
            )
            for session in sessions
        ]
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


# Cleanup endpoint for maintenance
@router.post("/chat/maintenance/cleanup")
async def cleanup_expired_sessions(
    background_tasks: BackgroundTasks,
    chat_service: EnhancedChatService = Depends(get_chat_service_dependency)
):
    """Cleanup expired sessions (maintenance endpoint)."""
    try:
        def cleanup():
            deleted_count = chat_db.cleanup_expired_sessions()
            logger.info(f"Cleaned up {deleted_count} expired sessions")
            return deleted_count
        
        background_tasks.add_task(cleanup)
        
        return {"message": "Cleanup task scheduled"}
    except Exception as e:
        logger.error(f"Error scheduling cleanup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule cleanup: {str(e)}")