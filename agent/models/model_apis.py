import os
from typing import List, Dict, Optional, Any
import os
from openai import OpenAI


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

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
    
    def chat_completions(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Make a chat completions API call.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Model to use (defaults to DEFAULT_MODEL or "claude-4-6-sonnet")
            tools: Optional list of tool definitions for function calling
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters to pass to the API      
            
        Returns:
            Full ChatCompletion response object from OpenAI
            
        Raises:
            RuntimeError: If the API request fails
            ValueError: If required parameters are invalid
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")

        response = self.client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            **kwargs
        )
        return response


if __name__ == "__main__":
    llm_client = LLMClient()
    response = llm_client.chat_completions(
        messages=[
            {"role": "user", "content": "what is distance of sun from earth"}
        ]
    )
    print(response)