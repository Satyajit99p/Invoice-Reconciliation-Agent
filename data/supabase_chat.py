"""
Enhanced Supabase client for chat operations.
Extends the existing SupabaseDB class with chat-specific functionality.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from supabase import create_client, Client
from data.supabase_da import SupabaseDB


class SupabaseChatDB(SupabaseDB):
    """Extended Supabase client with chat-specific operations."""
    
    def __init__(self):
        super().__init__()
        
    # Session Management
    def create_session(self, model_preference: str = "llama3.2", 
                      expires_hours: int = 24, 
                      current_invoice_id: Optional[str] = None,
                      metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a new chat session."""
        session_data = {
            "model_preference": model_preference,
            "expires_at": (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat(),
            "current_invoice_id": current_invoice_id,
            "metadata": metadata or {}
        }
        
        response = self.client.table("chat_sessions").insert(session_data).execute()
        return response.data[0] if response.data else {}
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID if not expired."""
        response = self.client.table("chat_sessions").select("*").eq("id", session_id).gt("expires_at", datetime.utcnow().isoformat()).execute()
        return response.data[0] if response.data else None
    
    def update_session(self, session_id: str, **kwargs) -> Dict[str, Any]:
        """Update session properties."""
        response = self.client.table("chat_sessions").update(kwargs).eq("id", session_id).execute()
        return response.data[0] if response.data else {}
    
    def extend_session(self, session_id: str, extend_hours: int = 24) -> bool:
        """Extend session expiration time."""
        new_expiry = (datetime.utcnow() + timedelta(hours=extend_hours)).isoformat()
        response = self.client.table("chat_sessions").update({"expires_at": new_expiry}).eq("id", session_id).execute()
        return len(response.data) > 0
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (cascades to messages and files)."""
        response = self.client.rpc("cleanup_expired_sessions").execute()
        return response.data if response.data else 0
    
    # Message Management
    def add_message(self, session_id: str, role: str, content: str, 
                   metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Add a message to the chat session."""
        message_data = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        
        response = self.client.table("chat_messages").insert(message_data).execute()
        return response.data[0] if response.data else {}
    
    def get_messages(self, session_id: str, limit: int = 100, 
                    offset: int = 0) -> List[Dict[str, Any]]:
        """Get messages for a session, ordered by creation time."""
        response = (self.client
                   .table("chat_messages")
                   .select("*")
                   .eq("session_id", session_id)
                   .order("created_at")
                   .range(offset, offset + limit - 1)
                   .execute())
        return response.data or []
    
    def get_conversation_history(self, session_id: str, 
                               include_metadata: bool = False) -> List[Dict[str, str]]:
        """Get conversation history formatted for LLM consumption."""
        messages = self.get_messages(session_id)
        
        formatted = []
        for msg in messages:
            formatted_msg = {
                "role": msg["role"],
                "content": msg["content"]
            }
            if include_metadata and msg.get("metadata"):
                formatted_msg["metadata"] = msg["metadata"]
            formatted.append(formatted_msg)
        
        return formatted
    
    def delete_messages(self, session_id: str) -> bool:
        """Delete all messages for a session."""
        response = self.client.table("chat_messages").delete().eq("session_id", session_id).execute()
        return True  # Delete operations don't return data
    
    # File Management
    def add_session_file(self, session_id: str, filename: str, 
                        file_path: str, file_size: int, 
                        mime_type: str) -> Dict[str, Any]:
        """Add a file record for the session."""
        file_data = {
            "session_id": session_id,
            "filename": filename,
            "file_path": file_path,
            "file_size": file_size,
            "mime_type": mime_type,
            "processing_status": "pending"
        }
        
        response = self.client.table("session_files").insert(file_data).execute()
        return response.data[0] if response.data else {}
    
    def update_file_status(self, file_id: str, status: str) -> bool:
        """Update file processing status."""
        response = (self.client
                   .table("session_files")
                   .update({"processing_status": status})
                   .eq("id", file_id)
                   .execute())
        return len(response.data) > 0
    
    def get_session_files(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all files for a session."""
        response = (self.client
                   .table("session_files")
                   .select("*")
                   .eq("session_id", session_id)
                   .order("uploaded_at", desc=True)
                   .execute())
        return response.data or []
    
    def get_file_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file record by file path."""
        response = (self.client
                   .table("session_files")
                   .select("*")
                   .eq("file_path", file_path)
                   .execute())
        return response.data[0] if response.data else None
    
    def delete_session_files(self, session_id: str) -> bool:
        """Delete all file records for a session."""
        response = self.client.table("session_files").delete().eq("session_id", session_id).execute()
        return True
    
    # Real-time Subscriptions (if using Supabase real-time)
    def subscribe_to_messages(self, session_id: str, callback):
        """Subscribe to new messages in a session."""
        return (self.client
                .channel(f"chat_{session_id}")
                .on('postgres_changes', 
                    event='INSERT', 
                    schema='public', 
                    table='chat_messages',
                    filter=f'session_id=eq.{session_id}',
                    callback=callback)
                .subscribe())
    
    def subscribe_to_files(self, session_id: str, callback):
        """Subscribe to file status changes in a session."""
        return (self.client
                .channel(f"files_{session_id}")
                .on('postgres_changes', 
                    event='*', 
                    schema='public', 
                    table='session_files',
                    filter=f'session_id=eq.{session_id}',
                    callback=callback)
                .subscribe())
    
    # Analytics and Management
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get session statistics."""
        session = self.get_session(session_id)
        if not session:
            return {}
        
        messages = self.get_messages(session_id)
        files = self.get_session_files(session_id)
        
        return {
            "session_id": session_id,
            "created_at": session["created_at"],
            "expires_at": session["expires_at"],
            "model_preference": session["model_preference"],
            "message_count": len(messages),
            "file_count": len(files),
            "user_messages": len([m for m in messages if m["role"] == "user"]),
            "assistant_messages": len([m for m in messages if m["role"] == "assistant"]),
            "current_invoice_id": session.get("current_invoice_id")
        }
    
    def list_active_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all active (non-expired) sessions."""
        response = (self.client
                   .table("chat_sessions")
                   .select("id, created_at, expires_at, model_preference, current_invoice_id")
                   .gt("expires_at", datetime.utcnow().isoformat())
                   .order("created_at", desc=True)
                   .limit(limit)
                   .execute())
        return response.data or []


# Singleton instance for easy importing
chat_db = SupabaseChatDB()