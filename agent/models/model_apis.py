import os
import requests
from typing import List, Dict, Optional, Any


class LLMClient:
    """
    API client for chat completions.
    
    Follows the project's existing patterns for external API integration
    with environment variable configuration and proper error handling.
    """
    
    def __init__(self):
        """
        Initialize the client with environment variable validation.
        
        Required environment variables:
        - BASE_URL: Base URL for the API
        - API_KEY: Bearer token for authentication
        
        Optional environment variables:
        - DEFAULT_MODEL: Default model to use (fallback to "claude-sonnet-4-6")
        
        Raises:
            RuntimeError: If required environment variables are not set
        """
        self.base_url = os.getenv("BASE_URL")
        self.api_key = os.getenv("API_KEY")
        self.default_model = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-6")
        
        if not self.base_url or not self.api_key:
            raise RuntimeError("BASE_URL and API_KEY must be set")
        
        # Ensure base_url has proper format for chat completions endpoint
        self.base_url = self.base_url.rstrip('/')
        self.chat_completions_url = f"{self.base_url}/chat/completions"
        
        # Set up default headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completions(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make a chat completions API call.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Model to use (defaults to DEFAULT_MODEL or "claude-4-6-sonnet")
            tools: Optional list of tool definitions for function calling
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters to pass to the API      
            
        Returns:
            Dictionary containing the API response
            
        Raises:
            RuntimeError: If the API request fails
            ValueError: If required parameters are invalid
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")
        
        # Prepare the request payload
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            **kwargs
        }
        
        # Add optional parameters if provided
        if tools:
            payload["tools"] = tools
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        try:
            response = requests.post(
                self.chat_completions_url,
                headers=self.headers,
                json=payload,
                timeout=60  # 60 second timeout
            )
            
            # Raise an exception for bad status codes
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"LLM API request failed: {str(e)}")
        except ValueError as e:
            raise RuntimeError(f"Failed to parse LLM API response: {str(e)}")


if __name__ == "__main__":
    llm_client = LLMClient()
    response = llm_client.chat_completions(
        messages=[
            {"role": "user", "content": "what is distance of sun from earth"}
        ]
    )
    print(response)