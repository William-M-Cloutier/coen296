import os
import base64
import imaplib
import email
from email.header import decode_header
import google.generativeai as genai
import resend  # Resend API for sending emails (bypasses SMTP)
from expense_agent import validate_reimbursement
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from logging_utils import get_logger
from drive_agent import (
    get_drive_service,
    list_files,
    search_files,
    download_file,
    upload_file,
    semantic_search,
    read_text_file,
    read_document
)

load_dotenv()
mcp = FastMCP("Gemini Server")

API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# Gmail credentials for READING emails (IMAP)
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")

# Resend credentials for SENDING emails (HTTPS API)
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

def list_emails_tool(max_results: int = 10, query: str = None):
    """List recent emails from the inbox using IMAP."""
    if not GMAIL_USER or not GMAIL_PASSWORD: 
        return "Error: GMAIL_USER or GMAIL_PASSWORD not set."
   
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        mail.select("inbox")
        status, messages = mail.search(None, "ALL")
        if status != "OK": return "No messages found."
       
        email_ids = messages[0].split()
        if not email_ids: return "No messages found."
       
        latest_email_ids = email_ids[-max_results:]
       
        output = []
        for e_id in reversed(latest_email_ids):
            try:
                _, msg_data = mail.fetch(e_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                       
                        subject = "(no subject)"
                        if msg["Subject"]:
                            try:
                                decoded = decode_header(msg["Subject"])[0]
                                if isinstance(decoded[0], bytes):
                                    subject = decoded[0].decode(decoded[1] if decoded[1] else "utf-8")
                                else:
                                    subject = decoded[0]
                            except:
                                subject = str(msg["Subject"])
                       
                        sender = msg.get("From", "(unknown)")
                        output.append(f"ID: {e_id.decode()} | From: {sender} | Subject: {subject}")
            except Exception as e:
                output.append(f"ID: {e_id.decode()} | Error: Could not parse email")
       
        mail.logout()
        return "\n".join(output) if output else "No emails found."
    except Exception as e: 
        return f"Error: {e}"

def read_email_tool(message_id: str):
    """Read full content of an email by ID using IMAP."""
    if not GMAIL_USER or not GMAIL_PASSWORD: 
        return "Error: GMAIL_USER or GMAIL_PASSWORD not set."
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        mail.select("inbox")
       
        _, msg_data = mail.fetch(message_id.encode(), "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
       
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()
           
        mail.logout()
        return f"Subject: {msg['Subject']}\nFrom: {msg['From']}\n\nBody:\n{body}"
    except Exception as e: 
        return f"Error: {e}"

def send_email_tool(to: str, subject: str, body: str):
    """Send an email using Resend API (HTTPS, not SMTP)."""
    if not RESEND_API_KEY or not RESEND_FROM_EMAIL:
        return "Error: RESEND_API_KEY or RESEND_FROM_EMAIL not set in environment variables."
    
    try:
        params = {
            "from": RESEND_FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "text": body
        }
        
        email_response = resend.Emails.send(params)
        return f"Email sent successfully! ID: {email_response['id']}"
    except Exception as e:
        return f"Error sending email via Resend: {e}"

# Drive tools
def list_drive_files_tool(max_results: int = 10, query: str = None):
    try:
        return list_files(max_results=max_results, query=query)
    except Exception as e:
        return f"Error listing Drive files: {e}"

def search_drive_files_tool(search_term: str, use_semantic: bool = False):
    try:
        return search_files(search_term=search_term, use_semantic=use_semantic)
    except Exception as e:
        return f"Error searching Drive files: {e}"

def download_drive_file_tool(file_id: str, destination: str = None):
    try:
        return download_file(file_id=file_id, destination=destination)
    except Exception as e:
        return f"Error downloading file: {e}"

def upload_drive_file_tool(filepath: str, folder_id: str = None):
    try:
        return upload_file(filepath=filepath, folder_id=folder_id)
    except Exception as e:
        return f"Error uploading file: {e}"

def semantic_search_tool(query: str, max_files: int = 10):
    try:
        return semantic_search(query=query, max_files=max_files)
    except Exception as e:
        return f"Error in content search: {e}"

def read_drive_document_tool(file_id: str):
    try:
        return read_document(file_id=file_id)
    except Exception as e:
        return f"Error reading document: {e}"

def validate_reimbursement_tool(receipt_path: str):
    try:
        return validate_reimbursement(receipt_path=receipt_path)
    except Exception as e:
        return f"Error validating reimbursement: {e}"

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
    """Ask the AI Agent to perform an action."""
    if not API_KEY: return "Error: GEMINI_API_KEY not set."
    logger = get_logger()
    
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
    
    chat = model.start_chat(enable_automatic_function_calling=False)
    
    try:
        response = chat.send_message(request)
        
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
                        tool_result = tools_map[tool_name](**args)
                    except Exception as e:
                        tool_result = f"Error executing {tool_name}: {str(e)}"
                
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
