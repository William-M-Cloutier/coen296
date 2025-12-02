import os
import google.generativeai as genai
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from logging_utils import get_logger

# Import Gmail API tools (Bypasses SMTP blocks)
from gmail_agent import (
    list_emails as list_emails_tool,
    read_email as read_email_tool,
    send_email as send_email_tool
)

# Import Drive agent functions
from drive_agent import (
    list_files as list_drive_files_tool,
    search_files as search_drive_files_tool,
    download_file as download_drive_file_tool,
    upload_file as upload_drive_file_tool,
    semantic_search as semantic_search_tool,
    read_document as read_drive_document_tool
)

# Import Expense agent function
from expense_agent import validate_reimbursement as validate_reimbursement_tool

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Gemini Server")

# Configure Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# Map of tool names to functions for execution
tools_map = {
    'list_emails': list_emails_tool,
    'read_email': read_email_tool,
    'send_email': send_email_tool,
    'list_drive_files': list_drive_files_tool,
    'search_drive_files': search_drive_files_tool,
    'download_drive_file': download_drive_file_tool,
    'upload_drive_file': upload_drive_file_tool,
    'semantic_search': semantic_search_tool,
    'validate_reimbursement': validate_reimbursement_tool,
    'read_drive_document': read_drive_document_tool
}

@mcp.tool()
def agent_action(request: str) -> str:
    """
    Ask the AI Agent to perform an action.
    """
    if not API_KEY: return "Error: GEMINI_API_KEY not set."
    logger = get_logger()
    
    # 1. Initialize Model with Tools
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        tools=[
            list_emails_tool, read_email_tool, send_email_tool,
            list_drive_files_tool, search_drive_files_tool, download_drive_file_tool,
            upload_drive_file_tool, semantic_search_tool,
            read_drive_document_tool,
            validate_reimbursement_tool
        ],
        system_instruction="You are an AI agent with access to tools. Call tools only with valid arguments as defined. For upload_drive_file_tool, require 'filepath' (local path) and optional 'folder_id'. If args are missing from request, ask for clarification instead of guessing. If the request includes 'Attached files:' followed by comma-separated file paths, treat those as the local 'filepath' arguments for upload (call the tool separately for each file if multiple). For expense reimbursement requests, use validate_reimbursement_tool with the receipt filepath from attached files (assume one file is the receipt; deny if no file)."
    )
    
    # 2. Start Chat Session (Manual Function Calling)
    chat = model.start_chat(enable_automatic_function_calling=False)
    
    try:
        # 3. Send initial message
        response = chat.send_message(request)
        
        # 4. Loop to handle tool calls (max 10 turns)
        for _ in range(10):
            if not response.candidates or not response.candidates[0].content.parts:
                break
                
            part = response.candidates[0].content.parts[0]
            
            if part.function_call:
                fc = part.function_call
                tool_name = fc.name
                args = dict(fc.args)
                
                logger.log_tool_call(tool_name, args)
                
                tool_result = "Error: Tool not found"
                if tool_name in tools_map:
                    try:
                        # Execute the tool
                        # Note: If tools are FastMCP objects, they might need special handling
                        # But usually they are callables.
                        tool_result = tools_map[tool_name](**args)
                    except Exception as e:
                        tool_result = f"Error executing {tool_name}: {str(e)}"
                
                # Send result back
                response = chat.send_message(
                    {
                        "role": "function",
                        "parts": [
                            {
                                "function_response": {
                                    "name": tool_name,
                                    "response": {"result": tool_result}
                                }
                            }
                        ]
                    }
                )
            else:
                if response.text:
                    result_text = response.text
                    logger.log_model_response(
                        model_name="gemini-2.5-flash (agent_action)",
                        prompt=request,
                        response=result_text
                    )
                    return result_text
                break
                
        if response.text:
            return response.text
        else:
            return "No final response generated after tool calls."

    except Exception as e:
        error_msg = f"Agent Error: {str(e)}"
        logger.log_error(
            error_type="agent_action_exception",
            error_message=str(e),
            context="agent_action"
        )
        return error_msg

@mcp.tool()
def ask_gemini(prompt: str) -> str:
    """Ask Gemini a general question (no tools)."""
    if not API_KEY: return "Error: GEMINI_API_KEY not set."
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    mcp_port = int(os.environ.get('MCP_PORT', 8000))
    mcp.run(transport="sse")
