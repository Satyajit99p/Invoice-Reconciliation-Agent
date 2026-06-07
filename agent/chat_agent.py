import ollama
from agent.tool_selector_model import SemanticMatcher
from agent.models.model_apis import LLMClient
from agent.models.response_handler import ResponseHandler
from agent.mcp_server import (
    get_excel_total,
    get_system_total,
    compare_totals,
    get_missing_tracking,
    get_duplicate_tracking,
    get_mismatched_invoicelines,
    get_failed_invoicelines,
    get_discrepancies,
    suggest_business_rules,
)
import os
from dotenv import load_dotenv
load_dotenv()

# Global registry for schemas and executable functions
TOOL_SCHEMAS = []
TOOL_REGISTRY = {}

# Decorator to automatically register tools
def register_tool(schema):
    def decorator(func):
        TOOL_SCHEMAS.append(schema)
        TOOL_REGISTRY[schema['function']['name']] = func
        return func
    return decorator



# --- MCP Tools: Invoice Reconciliation ---
register_tool({
    'type': 'function',
    'function': {
        'name': 'get_excel_total',
        'description': 'This calculates the total amount for the invoices present in the uploaded excel file.',
        'parameters': {
            'type': 'object',
            'properties': {'file_path': {'type': 'string'}},
            'required': ['file_path'],
        },
    },
})(get_excel_total)

register_tool({
    'type': 'function',
    'function': {
        'name': 'get_system_total',
        'description': 'This function retrieves the total amount for a single invoice already present in system',
        'parameters': {
            'type': 'object',
            'properties': {'invoice_id': {'type': 'string'}},
            'required': ['invoice_id'],
        },
    },
})(get_system_total)

register_tool({
    'type': 'function',
    'function': {
        'name': 'compare_totals',
        'description': 'Compare Excel and system totals.',
        'parameters': {
            'type': 'object',
            'properties': {
                'excel_total': {'type': 'number'},
                'system_total': {'type': 'number'},
            },
            'required': ['excel_total', 'system_total'],
        },
    },
})(compare_totals)

register_tool({
    'type': 'function',
    'function': {
        'name': 'get_missing_tracking',
        'description': 'Retrieve invoices with missing tracking numbers.',
        'parameters': {
            'type': 'object',
            'properties': {'invoice_id': {'type': 'string'}},
            'required': ['invoice_id'],
        },
    },
})(get_missing_tracking)

register_tool({
    'type': 'function',
    'function': {
        'name': 'get_duplicate_tracking',
        'description': 'Retrieve duplicate tracking records.',
        'parameters': {
            'type': 'object',
            'properties': {'invoice_id': {'type': 'string'}},
            'required': ['invoice_id'],
        },
    },
})(get_duplicate_tracking)

register_tool({
    'type': 'function',
    'function': {
        'name': 'get_mismatched_invoicelines',
        'description': 'Retrieve mismatched invoice lines.',
        'parameters': {
            'type': 'object',
            'properties': {'invoice_id': {'type': 'string'}},
            'required': ['invoice_id'],
        },
    },
})(get_mismatched_invoicelines)

register_tool({
    'type': 'function',
    'function': {
        'name': 'get_failed_invoicelines',
        'description': 'Retrieve failed invoice line records.',
        'parameters': {
            'type': 'object',
            'properties': {'invoice_id': {'type': 'string'}},
            'required': ['invoice_id'],
        },
    },
})(get_failed_invoicelines)

register_tool({
    'type': 'function',
    'function': {
        'name': 'get_discrepancies',
        'description': 'Retrieve all invoice discrepancies.',
        'parameters': {
            'type': 'object',
            'properties': {'invoice_id': {'type': 'string'}},
            'required': ['invoice_id'],
        },
    },
})(get_discrepancies)

register_tool({
    'type': 'function',
    'function': {
        'name': 'suggest_business_rules',
        'description': 'Retrieve business rules relevant to invoice failures.',
        'parameters': {
            'type': 'object',
            'properties': {
                'status_messages': {
                    'type': 'array',
                    'items': {'type': 'string'},
                },
            },
            'required': ['status_messages'],
        },
    },
})(suggest_business_rules)


def process_user_intent(user_query, filtered_tool_name=None):
    """
    user_query: The text from the user
    filtered_tool_name: The tool your cosine similarity model picked. 
                         If provided, we only pass that specific tool to the model.
    """
    # 1. Determine which tools to send to the model
    if filtered_tool_name and filtered_tool_name in TOOL_REGISTRY:
        # Optimization: Only give the model the exact tool your router picked
        available_tools = [t for t in TOOL_SCHEMAS if t['function']['name'] == filtered_tool_name]
    else:
        # Fallback: Let the model choose from all available tools
        available_tools = TOOL_SCHEMAS

    # 2. Get model response and normalize it
    messages = [{'role': 'user', 'content': user_query}]
    active_model = os.getenv("ACTIVE_MODEL")

    try:
        if active_model == "ollama":
            raw_response = ollama.chat(
                model='llama3.2',
                messages=messages,
                tools=available_tools
            )
            normalized_response = ResponseHandler.handle_ollama_response(raw_response)
        else:
            llm_client = LLMClient()
            raw_response = llm_client.chat_completions(
                messages=messages,
                tools=available_tools
            )
            normalized_response = ResponseHandler.handle_openai_response(raw_response)
    except Exception as e:
        return f"Error processing response: {e}"
    
    # 3. Dynamic Execution Loop
    if normalized_response.has_tool_calls:
        for call in normalized_response.tool_calls:
            func_name = call['function']['name']
            func_args = call['function']['arguments']
            
            if func_name in TOOL_REGISTRY:
                print(f"Executing: {func_name} with arguments {func_args}")
                
                # Dynamic Execution via unpacking Python kwargs (**)
                try:
                    tool_result = TOOL_REGISTRY[func_name](**func_args)
                except TypeError as e:
                    tool_result = f"Error executing tool: Missing or invalid arguments. Details: {e}"
                
                # Create message format for tool response
                tool_message = {
                    'role': 'tool', 
                    'content': str(tool_result), 
                    'name': func_name
                }

                # Get original message format from raw response
                if 'message' in normalized_response.raw_response:
                    response_message = normalized_response.raw_response['message']
                else:
                    response_message = {'role': 'assistant', 'content': normalized_response.content}
                
                # 4. Generate final conversational response
                # For now, use the active model for final response too
                if active_model == "ollama":
                    final_response = ollama.chat(
                        model='llama3.2',
                        messages=messages + [response_message, tool_message]
                    )
                    return final_response['message']['content']
                else:
                    final_response = llm_client.chat_completions(
                        messages=messages + [response_message, tool_message]
                    )
                    return final_response.choices[0].message.content
                
    return normalized_response.content or "No response content available"

if __name__ == "__main__":

    tools_available = {t['function']['name']: t['function']['description'] for t in TOOL_SCHEMAS}

    _tool_selector = SemanticMatcher(tools_available)
    
    query = "Can you fetch me total amount for invoice INV-001?"
    tool_name = _tool_selector.predict(query)

    print(process_user_intent(query, filtered_tool_name=tool_name["predicted_class"]))
    print("-" * 50)