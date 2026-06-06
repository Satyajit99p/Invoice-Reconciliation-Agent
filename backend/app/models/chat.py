"""
Pydantic models for chat API requests and responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class MessageRole(str, Enum):
    """Chat message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ProcessStep(str, Enum):
    """Process steps for real-time updates."""
    FILE_PROCESSING = "file_processing"
    QUERY_ANALYSIS = "query_analysis"
    TOOL_SELECTION = "tool_selection"
    TOOL_EXECUTION = "tool_execution"
    RESPONSE_GENERATION = "response_generation"


class ProcessStatus(str, Enum):
    """Status for process steps."""
    STARTING = "starting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class FileStatus(str, Enum):
    """File processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


# Request Models
class CreateSessionRequest(BaseModel):
    """Request to create a new chat session."""
    model_preference: str = "llama3.2"
    expires_hours: int = Field(default=24, ge=1, le=168)  # 1 hour to 1 week
    current_invoice_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SendMessageRequest(BaseModel):
    """Request to send a message in a chat session."""
    content: str = Field(..., min_length=1, max_length=10000)
    role: MessageRole = MessageRole.USER
    metadata: Optional[Dict[str, Any]] = None


class UpdateSessionRequest(BaseModel):
    """Request to update session properties."""
    model_preference: Optional[str] = None
    current_invoice_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SelectModelRequest(BaseModel):
    """Request to select/change model for a session."""
    model_name: str
    provider: str = Field(..., pattern="^(ollama|openai|anthropic)$")


# Response Models
class ToolCall(BaseModel):
    """Tool call information."""
    name: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class ProcessStepInfo(BaseModel):
    """Process step information."""
    step: ProcessStep
    status: ProcessStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    """Chat message response."""
    id: str
    session_id: str
    role: MessageRole
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    
    # Enhanced response data
    tool_calls: Optional[List[ToolCall]] = None
    model_used: Optional[str] = None
    processing_time: Optional[float] = None
    process_steps: Optional[List[ProcessStepInfo]] = None
    confidence: Optional[float] = None


class SessionResponse(BaseModel):
    """Chat session response."""
    id: str
    created_at: datetime
    expires_at: datetime
    model_preference: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    current_invoice_id: Optional[str] = None
    
    # Optional statistics
    message_count: Optional[int] = None
    file_count: Optional[int] = None


class FileResponse(BaseModel):
    """File upload response."""
    id: str
    session_id: str
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    processing_status: FileStatus
    uploaded_at: datetime


class ConversationResponse(BaseModel):
    """Full conversation response."""
    session: SessionResponse
    messages: List[MessageResponse]
    files: Optional[List[FileResponse]] = None


class SessionStatsResponse(BaseModel):
    """Session statistics response."""
    session_id: str
    created_at: datetime
    expires_at: datetime
    model_preference: str
    message_count: int
    file_count: int
    user_messages: int
    assistant_messages: int
    current_invoice_id: Optional[str] = None


class ModelInfo(BaseModel):
    """Model information."""
    name: str
    provider: str
    available: bool
    description: Optional[str] = None


class ModelsResponse(BaseModel):
    """Available models response."""
    models: Dict[str, List[ModelInfo]]
    default_model: str
    current_model: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    code: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    environment: str
    version: str
    services: Optional[Dict[str, bool]] = None


# WebSocket Message Models
class WebSocketMessage(BaseModel):
    """Base WebSocket message."""
    type: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ProcessStepMessage(WebSocketMessage):
    """Process step WebSocket message."""
    type: str = "process_step"
    step: ProcessStep
    status: ProcessStatus
    details: Optional[Dict[str, Any]] = None


class ToolExecutionMessage(WebSocketMessage):
    """Tool execution WebSocket message."""
    type: str = "tool_execution"
    tool_name: str
    status: ProcessStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ModelUpdateMessage(WebSocketMessage):
    """Model update WebSocket message."""
    type: str = "model_update"
    model_name: str
    status: str = "active"


class FileUpdateMessage(WebSocketMessage):
    """File update WebSocket message."""
    type: str = "file_update"
    filename: str
    status: FileStatus
    progress: Optional[float] = None
    error: Optional[str] = None


class ErrorMessage(WebSocketMessage):
    """Error WebSocket message."""
    type: str = "error"
    message: str
    code: str = "general_error"


# Validation helpers
class ChatValidators:
    """Validation helpers for chat models."""
    
    @staticmethod
    def validate_session_id(v: str) -> str:
        """Validate session ID format."""
        if not v or len(v) < 10:
            raise ValueError("Invalid session ID")
        return v
    
    @staticmethod
    def validate_model_name(v: str) -> str:
        """Validate model name."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Model name cannot be empty")
        return v.strip()
    
    @staticmethod
    def validate_file_size(v: int, max_size: int = 10485760) -> int:  # 10MB default
        """Validate file size."""
        if v <= 0:
            raise ValueError("File size must be positive")
        if v > max_size:
            raise ValueError(f"File size exceeds maximum allowed size of {max_size} bytes")
        return v