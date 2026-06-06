"""
Enhanced chat service wrapper around existing chat_agent.py.
Provides structured responses, session management, and WebSocket updates.
"""

import asyncio
import time
import logging
import traceback
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from data.supabase_chat import chat_db
from app.core.config import settings
from app.core.websocket_manager import ConnectionManager
from app.models.chat import ProcessStep, ProcessStatus, ToolCall, ProcessStepInfo

logger = logging.getLogger(__name__)


class EnhancedChatService:
    """Enhanced chat service with structured responses and real-time updates."""
    
    def __init__(self, websocket_manager: ConnectionManager):
        self.websocket_manager = websocket_manager
        self.semantic_matcher = None
        self._initialize_semantic_matcher()
    
    def _initialize_semantic_matcher(self):
        """Initialize semantic matcher (expensive operation - do once)."""
        try:
            from agent.chat_agent import TOOL_SCHEMAS
            from agent.tool_selector_model import SemanticMatcher
            
            tools_available = {
                t['function']['name']: t['function']['description'] 
                for t in TOOL_SCHEMAS
            }
            self.semantic_matcher = SemanticMatcher(tools_available)
            logger.info("✅ SemanticMatcher initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ SemanticMatcher initialization failed: {e}")
            self.semantic_matcher = None
    
    async def process_message(self, session_id: str, user_message: str, 
                            metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process a user message with enhanced features and real-time updates.
        
        Returns structured response with tool calls, timing, and process steps.
        """
        start_time = time.time()
        process_steps = []
        tool_calls = []
        
        try:
            # Get session info
            session = chat_db.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found or expired")
            
            model_used = session.get("model_preference", settings.DEFAULT_MODEL)
            
            # Step 1: Query Analysis
            await self._update_process_step(
                session_id, ProcessStep.QUERY_ANALYSIS, ProcessStatus.STARTING
            )
            
            step_start = time.time()
            filtered_tool_name = None
            confidence = None
            
            if self.semantic_matcher:
                try:
                    prediction = self.semantic_matcher.predict(user_message)
                    filtered_tool_name = prediction.get("predicted_class")
                    confidence = prediction.get("confidence")
                    
                    await self._update_process_step(
                        session_id, ProcessStep.QUERY_ANALYSIS, ProcessStatus.COMPLETED,
                        {"predicted_tool": filtered_tool_name, "confidence": confidence}
                    )
                except Exception as e:
                    logger.warning(f"Semantic matching failed: {e}")
                    await self._update_process_step(
                        session_id, ProcessStep.QUERY_ANALYSIS, ProcessStatus.COMPLETED,
                        {"error": "Semantic matching unavailable"}
                    )
            else:
                await self._update_process_step(
                    session_id, ProcessStep.QUERY_ANALYSIS, ProcessStatus.COMPLETED,
                    {"note": "Using all available tools"}
                )
            
            step_end = time.time()
            process_steps.append(ProcessStepInfo(
                step=ProcessStep.QUERY_ANALYSIS,
                status=ProcessStatus.COMPLETED,
                start_time=datetime.fromtimestamp(step_start),
                end_time=datetime.fromtimestamp(step_end),
                details={"tool_prediction": filtered_tool_name, "confidence": confidence}
            ))
            
            # Step 2: Tool Selection & Execution
            await self._update_process_step(
                session_id, ProcessStep.TOOL_SELECTION, ProcessStatus.STARTING
            )
            
            # Add conversation history
            conversation_history = chat_db.get_conversation_history(session_id)
            
            # Execute chat agent with monitoring
            step_start = time.time()
            
            response_content, agent_tool_calls = await self._execute_chat_agent(
                session_id, user_message, conversation_history, 
                filtered_tool_name, model_used
            )
            
            step_end = time.time()
            tool_calls.extend(agent_tool_calls)
            
            # Step 3: Response Generation (already completed by agent)
            await self._update_process_step(
                session_id, ProcessStep.RESPONSE_GENERATION, ProcessStatus.COMPLETED
            )
            
            process_steps.append(ProcessStepInfo(
                step=ProcessStep.TOOL_EXECUTION,
                status=ProcessStatus.COMPLETED,
                start_time=datetime.fromtimestamp(step_start),
                end_time=datetime.fromtimestamp(step_end),
                details={"tools_executed": len(agent_tool_calls)}
            ))
            
            # Save messages to database
            chat_db.add_message(session_id, "user", user_message, metadata)
            
            assistant_metadata = {
                "tool_calls": [tc.dict() for tc in tool_calls],
                "model_used": model_used,
                "processing_time": time.time() - start_time,
                "confidence": confidence,
                "process_steps": [step.dict() for step in process_steps]
            }
            
            assistant_message = chat_db.add_message(
                session_id, "assistant", response_content, assistant_metadata
            )
            
            # Return structured response
            return {
                "id": assistant_message["id"],
                "session_id": session_id,
                "role": "assistant",
                "content": response_content,
                "metadata": assistant_metadata,
                "created_at": assistant_message["created_at"],
                "tool_calls": tool_calls,
                "model_used": model_used,
                "processing_time": time.time() - start_time,
                "process_steps": process_steps,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Error processing message for session {session_id}: {e}")
            logger.error(traceback.format_exc())
            
            # Send error notification
            await self.websocket_manager.send_error(
                session_id, 
                f"I'm experiencing technical difficulties: {str(e)}", 
                "processing_error"
            )
            
            # Save error message  
            error_response = "I'm experiencing technical difficulties. Please try again in a moment."
            chat_db.add_message(session_id, "user", user_message, metadata)
            error_message = chat_db.add_message(
                session_id, "assistant", error_response, 
                {"error": str(e), "processing_time": time.time() - start_time}
            )
            
            return {
                "id": error_message["id"],
                "session_id": session_id,
                "role": "assistant", 
                "content": error_response,
                "metadata": {"error": str(e)},
                "created_at": error_message["created_at"],
                "error": str(e)
            }
    
    async def _execute_chat_agent(self, session_id: str, user_message: str, 
                                 conversation_history: List[Dict], 
                                 filtered_tool_name: Optional[str],
                                 model_used: str) -> Tuple[str, List[ToolCall]]:
        """Execute the chat agent with monitoring."""
        from agent.chat_agent import process_user_intent
        
        await self._update_process_step(
            session_id, ProcessStep.TOOL_EXECUTION, ProcessStatus.STARTING
        )
        
        tool_calls = []
        
        try:
            # Execute in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response_content = await loop.run_in_executor(
                None, process_user_intent, user_message, filtered_tool_name
            )
            
            # Note: The current chat_agent doesn't return tool call details
            # We would need to modify it to get actual tool execution info
            # For now, we'll infer from the filtered_tool_name
            if filtered_tool_name:
                tool_calls.append(ToolCall(
                    name=filtered_tool_name,
                    arguments={},  # Would need agent modification to get actual args
                    result={"inferred": True},
                    execution_time=None
                ))
                
                await self.websocket_manager.send_tool_execution(
                    session_id, filtered_tool_name, "completed"
                )
            
            await self._update_process_step(
                session_id, ProcessStep.TOOL_EXECUTION, ProcessStatus.COMPLETED
            )
            
            return response_content, tool_calls
            
        except Exception as e:
            await self.websocket_manager.send_tool_execution(
                session_id, filtered_tool_name or "unknown", "failed", error=str(e)
            )
            raise e
    
    async def _update_process_step(self, session_id: str, step: ProcessStep, 
                                  status: ProcessStatus, details: Optional[Dict] = None):
        """Update process step via WebSocket."""
        await self.websocket_manager.send_process_step(
            session_id, step.value, status.value, details
        )
    
    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get formatted conversation history."""
        return chat_db.get_conversation_history(session_id)
    
    def create_session(self, **kwargs) -> Dict[str, Any]:
        """Create a new chat session."""
        return chat_db.create_session(**kwargs)
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        return chat_db.get_session(session_id)
    
    def update_session(self, session_id: str, **kwargs) -> Dict[str, Any]:
        """Update session properties."""
        return chat_db.update_session(session_id, **kwargs)
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get session statistics."""
        return chat_db.get_session_stats(session_id)
    
    async def change_model(self, session_id: str, model_name: str, provider: str) -> bool:
        """Change model for a session."""
        try:
            # Validate model availability
            available_models = self._get_available_models()
            if provider not in available_models or model_name not in [m["name"] for m in available_models[provider]]:
                raise ValueError(f"Model {model_name} not available for provider {provider}")
            
            # Update session
            chat_db.update_session(session_id, model_preference=model_name)
            
            # Notify via WebSocket
            await self.websocket_manager.send_model_update(session_id, model_name)
            
            return True
        except Exception as e:
            logger.error(f"Error changing model for session {session_id}: {e}")
            return False
    
    def _get_available_models(self) -> Dict[str, List[Dict]]:
        """Get available models from configuration."""
        from app.core.config import get_available_models
        
        models_dict = get_available_models()
        
        # Convert to expected format
        formatted_models = {}
        for provider, model_names in models_dict.items():
            formatted_models[provider] = [
                {"name": name, "available": True} 
                for name in model_names
            ]
        
        return formatted_models


# Global service instance
chat_service = None

def get_chat_service(websocket_manager: ConnectionManager) -> EnhancedChatService:
    """Get or create chat service instance."""
    global chat_service
    if chat_service is None:
        chat_service = EnhancedChatService(websocket_manager)
    return chat_service