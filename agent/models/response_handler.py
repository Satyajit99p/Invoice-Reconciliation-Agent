import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union
from openai.types.chat import ChatCompletion


@dataclass
class NormalizedResponse:
    """
    Normalized response structure for both OpenAI and Ollama responses.
    
    Attributes:
        content: The text content of the response
        tool_calls: List of normalized tool calls in dictionary format
        has_tool_calls: Boolean indicating if tool calls are present
        raw_response: The original response object for debugging/advanced usage
    """
    content: Optional[str]
    tool_calls: List[Dict[str, Any]]
    has_tool_calls: bool
    raw_response: Any


class ResponseHandler:
    """
    Unified handler for normalizing OpenAI and Ollama responses into a consistent format.
    
    This class provides static methods to convert different response formats into
    a standardized NormalizedResponse object that can be used consistently
    throughout the application.
    """
    
    @staticmethod
    def handle_ollama_response(response: Dict[str, Any]) -> NormalizedResponse:
        """
        Handle Ollama's dictionary-based response format.
        
        Args:
            response: Ollama response dictionary
            
        Returns:
            NormalizedResponse with normalized tool calls and content
            
        Raises:
            ValueError: If response format is invalid
        """
        if not isinstance(response, dict):
            raise ValueError("Ollama response must be a dictionary")
        
        try:
            message = response.get('message', {})
            content = message.get('content')
            tool_calls = message.get('tool_calls', [])
            
            # Normalize tool calls - Ollama already provides them in dict format
            normalized_tool_calls = []
            for call in tool_calls:
                if isinstance(call, dict) and 'function' in call:
                    # Ensure arguments are parsed as dict if they're JSON string
                    func_data = call['function']
                    arguments = func_data.get('arguments', {})
                    
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            arguments = {}
                    
                    normalized_call = {
                        'function': {
                            'name': func_data.get('name', ''),
                            'arguments': arguments
                        }
                    }
                    normalized_tool_calls.append(normalized_call)
            
            return NormalizedResponse(
                content=content,
                tool_calls=normalized_tool_calls,
                has_tool_calls=len(normalized_tool_calls) > 0,
                raw_response=response
            )
            
        except Exception as e:
            raise ValueError(f"Failed to parse Ollama response: {e}")
    
    @staticmethod
    def handle_openai_response(response: ChatCompletion) -> NormalizedResponse:
        """
        Handle OpenAI's ChatCompletion object response format.
        
        Args:
            response: OpenAI ChatCompletion object
            
        Returns:
            NormalizedResponse with normalized tool calls and content
            
        Raises:
            ValueError: If response format is invalid
        """
        try:
            if not hasattr(response, 'choices') or not response.choices:
                raise ValueError("OpenAI response must have choices")
            
            message = response.choices[0].message
            content = message.content
            tool_calls = getattr(message, 'tool_calls', None) or []
            
            # Normalize tool calls - convert from OpenAI objects to dicts
            normalized_tool_calls = []
            for call in tool_calls:
                try:
                    # Access as object attributes, not dictionary keys
                    function_name = call.function.name
                    function_arguments = call.function.arguments
                    
                    # Parse arguments if they're JSON string
                    if isinstance(function_arguments, str):
                        try:
                            arguments = json.loads(function_arguments)
                        except json.JSONDecodeError:
                            arguments = {}
                    else:
                        arguments = function_arguments or {}
                    
                    normalized_call = {
                        'function': {
                            'name': function_name,
                            'arguments': arguments
                        }
                    }
                    normalized_tool_calls.append(normalized_call)
                    
                except (AttributeError, TypeError) as e:
                    # Skip malformed tool calls but continue processing
                    print(f"Warning: Skipping malformed tool call: {e}")
                    continue
            
            return NormalizedResponse(
                content=content,
                tool_calls=normalized_tool_calls,
                has_tool_calls=len(normalized_tool_calls) > 0,
                raw_response=response
            )
            
        except Exception as e:
            raise ValueError(f"Failed to parse OpenAI response: {e}")
    
    @staticmethod
    def normalize_response(response: Union[Dict[str, Any], ChatCompletion], 
                          response_type: str) -> NormalizedResponse:
        """
        Convenience method to normalize responses based on type.
        
        Args:
            response: Either Ollama dict or OpenAI ChatCompletion object
            response_type: Either 'ollama' or 'openai'
            
        Returns:
            NormalizedResponse object
            
        Raises:
            ValueError: If response_type is invalid or response parsing fails
        """
        if response_type.lower() == 'ollama':
            return ResponseHandler.handle_ollama_response(response)
        elif response_type.lower() == 'openai':
            return ResponseHandler.handle_openai_response(response)
        else:
            raise ValueError(f"Unsupported response type: {response_type}")