"""
Model management API endpoints.
Handles model selection and availability for chat sessions.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends

from app.models.chat import ModelsResponse, ModelInfo, SelectModelRequest
from app.core.config import settings, get_available_models
from app.services.chat_service import get_chat_service, EnhancedChatService
from data.supabase_chat import chat_db

logger = logging.getLogger(__name__)

router = APIRouter()

def get_chat_service_dependency() -> EnhancedChatService:
    """Dependency to get chat service instance."""
    from app.main import manager
    return get_chat_service(manager)


@router.get("/models", response_model=ModelsResponse)
async def list_available_models():
    """Get list of available models across all providers."""
    try:
        models_dict = get_available_models()
        
        # Convert to structured format
        formatted_models = {}
        
        for provider, model_names in models_dict.items():
            formatted_models[provider] = []
            
            for model_name in model_names:
                # Check actual availability
                available = await check_model_availability(provider, model_name)
                
                description = get_model_description(provider, model_name)
                
                formatted_models[provider].append(ModelInfo(
                    name=model_name,
                    provider=provider,
                    available=available,
                    description=description
                ))
        
        return ModelsResponse(
            models=formatted_models,
            default_model=settings.DEFAULT_MODEL
        )
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.get("/models/{provider}")
async def list_provider_models(provider: str):
    """Get models for a specific provider."""
    try:
        if provider not in ["ollama", "openai", "anthropic"]:
            raise HTTPException(status_code=400, detail="Invalid provider")
        
        models_dict = get_available_models()
        
        if provider not in models_dict:
            return {"models": [], "provider": provider}
        
        models = []
        for model_name in models_dict[provider]:
            available = await check_model_availability(provider, model_name)
            description = get_model_description(provider, model_name)
            
            models.append(ModelInfo(
                name=model_name,
                provider=provider,
                available=available,
                description=description
            ))
        
        return {"models": models, "provider": provider}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing {provider} models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list {provider} models: {str(e)}")


@router.post("/models/select/{session_id}")
async def select_model_for_session(
    session_id: str,
    request: SelectModelRequest,
    chat_service: EnhancedChatService = Depends(get_chat_service_dependency)
):
    """Select/change model for a chat session."""
    try:
        # Verify session exists
        session = chat_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        # Validate model availability
        available = await check_model_availability(request.provider, request.model_name)
        if not available:
            raise HTTPException(
                status_code=400, 
                detail=f"Model {request.model_name} not available for provider {request.provider}"
            )
        
        # Update session model preference
        success = await chat_service.change_model(session_id, request.model_name, request.provider)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to change model")
        
        return {
            "message": "Model changed successfully",
            "session_id": session_id,
            "model_name": request.model_name,
            "provider": request.provider
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting model for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to select model: {str(e)}")


@router.get("/models/session/{session_id}")
async def get_session_model(
    session_id: str,
    chat_service: EnhancedChatService = Depends(get_chat_service_dependency)
):
    """Get current model for a chat session."""
    try:
        session = chat_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        model_preference = session.get("model_preference", settings.DEFAULT_MODEL)
        
        # Determine provider from model name
        provider = detect_model_provider(model_preference)
        
        return {
            "session_id": session_id,
            "model_name": model_preference,
            "provider": provider,
            "available": await check_model_availability(provider, model_preference)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session model: {str(e)}")


@router.get("/models/health")
async def check_models_health():
    """Check health/availability of all configured model providers."""
    try:
        health_status = {}
        
        # Check Ollama
        if settings.ollama_configured:
            health_status["ollama"] = await check_ollama_health()
        
        # Check OpenAI
        if settings.openai_configured:
            health_status["openai"] = await check_openai_health()
        
        # Check Anthropic
        if settings.anthropic_configured:
            health_status["anthropic"] = await check_anthropic_health()
        
        return {
            "status": "healthy" if any(health_status.values()) else "unhealthy",
            "providers": health_status
        }
    except Exception as e:
        logger.error(f"Error checking model health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check model health: {str(e)}")


# Helper functions
async def check_model_availability(provider: str, model_name: str) -> bool:
    """Check if a specific model is available."""
    try:
        if provider == "ollama":
            return await check_ollama_model_availability(model_name)
        elif provider == "openai":
            return await check_openai_model_availability(model_name)
        elif provider == "anthropic":
            return await check_anthropic_model_availability(model_name)
        else:
            return False
    except Exception as e:
        logger.warning(f"Error checking availability for {provider}:{model_name}: {e}")
        return False


async def check_ollama_health() -> bool:
    """Check if Ollama is available."""
    try:
        import ollama
        ollama.list()
        return True
    except Exception:
        return False


async def check_openai_health() -> bool:
    """Check if OpenAI API is available."""
    try:
        if not settings.openai_configured:
            return False
        
        # Could implement actual API check here
        # For now, just check if API key is configured
        return len(settings.OPENAI_API_KEY) > 0
    except Exception:
        return False


async def check_anthropic_health() -> bool:
    """Check if Anthropic API is available."""
    try:
        if not settings.anthropic_configured:
            return False
        
        # Could implement actual API check here
        # For now, just check if API key is configured
        return len(settings.ANTHROPIC_API_KEY) > 0
    except Exception:
        return False


async def check_ollama_model_availability(model_name: str) -> bool:
    """Check if specific Ollama model is available."""
    try:
        import ollama
        models = ollama.list()
        available_models = [model["name"] for model in models.get("models", [])]
        return model_name in available_models
    except Exception:
        return False


async def check_openai_model_availability(model_name: str) -> bool:
    """Check if specific OpenAI model is available."""
    try:
        # List of known OpenAI models
        known_models = ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o"]
        return model_name in known_models and settings.openai_configured
    except Exception:
        return False


async def check_anthropic_model_availability(model_name: str) -> bool:
    """Check if specific Anthropic model is available."""
    try:
        # List of known Anthropic models
        known_models = ["claude-3-sonnet", "claude-3-haiku", "claude-3-opus"]
        return model_name in known_models and settings.anthropic_configured
    except Exception:
        return False


def detect_model_provider(model_name: str) -> str:
    """Detect provider from model name."""
    if model_name.startswith("gpt-"):
        return "openai"
    elif model_name.startswith("claude-"):
        return "anthropic"
    else:
        return "ollama"


def get_model_description(provider: str, model_name: str) -> str:
    """Get description for a model."""
    descriptions = {
        "ollama": {
            "llama3.2": "Meta's Llama 3.2 model optimized for conversations",
            "llama3.1": "Meta's Llama 3.1 model with improved capabilities",
            "codellama": "Meta's specialized code generation model",
            "mistral": "Mistral AI's efficient language model"
        },
        "openai": {
            "gpt-4": "OpenAI's most capable model",
            "gpt-3.5-turbo": "Fast and cost-effective OpenAI model",
            "gpt-4-turbo": "Enhanced GPT-4 with improved speed",
            "gpt-4o": "Latest GPT-4 optimized model"
        },
        "anthropic": {
            "claude-3-sonnet": "Anthropic's balanced model for most tasks",
            "claude-3-haiku": "Anthropic's fastest model",
            "claude-3-opus": "Anthropic's most capable model"
        }
    }
    
    return descriptions.get(provider, {}).get(model_name, f"{provider} model: {model_name}")