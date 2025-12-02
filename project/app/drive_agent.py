"""
Google Drive Agent with Native Search
Integrates Drive API for file operations and content search
"""
import os
import io
from typing import List, Dict, Optional
from dotenv import load_dotenv
# Google Drive imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from mcp.server.fastmcp import FastMCP
# NEW IMPORT FOR PDF EXTRACTION
from pypdf import PdfReader
from logging_utils import get_logger


mcp = FastMCP("Drive Agent")
load_dotenv()
# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

# Get the directory of this script for consistent file paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

@mcp.tool()
def get_drive_service():
    """Authenticate and return the Drive service."""
    creds = None
    token_path = os.path.join(SCRIPT_DIR, './drive_token.json')
    credentials_path = os.path.join(SCRIPT_DIR, './drive_credentials.json')
    
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                print(f"Error: drive_credentials.json not found in {SCRIPT_DIR}.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

@mcp.tool()
def list_files(max_results: int = 10, query: str = None) -> str:
    """
    List files from Google Drive.
    
    Args:
        max_results: Maximum number of files to return
        query: Optional query string for filtering
    """
    logger = get_logger()
    logger.log_tool_call(
        tool_name="list_files",
        parameters={"max_results": max_results, "query": query}
    )
    try:
        service = get_drive_service()
        if not service:
            return "Error: Drive authentication required."
        
        results = service.files().list(
            pageSize=max_results,
            q=query,
            fields="files(id, name, mimeType, modifiedTime, size)"
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            return "No files found."
        
        output = ["Files found:"]
        for file in files:
            size = file.get('size', 'N/A')
            output.append(f"ID: {file['id']} | Name: {file['name']} | Type: {file['mimeType']} | Size: {size} bytes")
            
        logger.log_tool_call(
            tool_name="list_files",
            parameters={"max_results": max_results, "query": query},
            result=f"Found {len(files)} files"
        )
        return "\n".join(output)
    
    except Exception as e:
        logger.log_error(
            error_type="drive_list_files_error",
            error_message=str(e),
            context="list_files"
        )
        return f"Error listing files: {e}"

@mcp.tool()
def search_files(search_term: str, use_semantic: bool = False) -> str:
    """
    Search for files in Google Drive.
    
    Args:
        search_term: Term to search for
        use_semantic: If True, use native content search (fullText)
    """
    logger = get_logger()
    logger.log_tool_call(
        tool_name="search_files",
        parameters={"search_term": search_term, "use_semantic": use_semantic}
    )
    try:
        if use_semantic:
            # Use native content search
            return semantic_search(search_term, max_files=5)
        else:
            # Regular Drive API search by filename
            query = f"name contains '{search_term}'"
            return list_files(max_results=10, query=query)
    
    except Exception as e:
        logger.log_error(
            error_type="drive_search_error",
            error_message=str(e),
            context="search_files"
        )
        return f"Error searching files: {e}"

@mcp.tool()
def download_file(file_id: str, destination: str = None) -> str:
    """
    Download a file from Google Drive.
    
    Args:
        file_id: ID of the file to download
        destination: Optional local path to save file
    """
    logger = get_logger()
    logger.log_tool_call(
        tool_name="download_file",
        parameters={"file_id": file_id, "destination": destination}
    )
    try:
        service = get_drive_service()
        if not service:
            return "Error: Drive authentication required."
        
        # Get file metadata
        file_metadata = service.files().get(fileId=file_id, fields='name,mimeType').execute()
        filename = file_metadata['name']
        
        # Download file
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        # Save to file
        save_path = destination if destination else filename
        
        # Ensure directory exists
        if os.path.dirname(save_path):
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
        with open(save_path, 'wb') as f:
            f.write(fh.getbuffer())
            
        logger.log_tool_call(
            tool_name="download_file",
            parameters={"file_id": file_id, "destination": destination},
            result=f"File downloaded successfully to: {save_path}"
        )
        return f"File downloaded successfully to: {save_path}"
    
    except Exception as e:
        logger.log_error(
            error_type="drive_download_error",
            error_message=str(e),
            context="download_file"
        )
        return f"Error downloading file: {e}"

@mcp.tool()
def upload_file(filepath: str, folder_id: str = None) -> str:
    """
    Upload a file to Google Drive.
    
    Args:
        filepath: Local path to file to upload
        folder_id: Optional folder ID to upload to
    """
    logger = get_logger()
    logger.log_tool_call(
        tool_name="upload_file",
        parameters={"filepath": filepath, "folder_id": folder_id}
    )
    try:
        if not os.path.exists(filepath):
            return f"Error: File not found at {filepath}"
            
        service = get_drive_service()
        if not service:
            return "Error: Drive authentication required."
        
        file_metadata = {'name': os.path.basename(filepath)}
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        media = MediaFileUpload(filepath, resumable=True)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name'
        ).execute()
        
        logger.log_tool_call(
            tool_name="upload_file",
            parameters={"filepath": filepath, "folder_id": folder_id},
            result=f"File uploaded successfully! ID: {file.get('id')}, Name: {file.get('name')}"
        )
        return f"File uploaded successfully! ID: {file.get('id')}, Name: {file.get('name')}"
    
    except Exception as e:
        logger.log_error(
            error_type="drive_upload_error",
            error_message=str(e),
            context="upload_file"
        )
        return f"Error uploading file: {e}"

@mcp.tool()
def semantic_search(query: str, max_files: int = 10) -> str:
    """
    Search for files by content using Google Drive's native full-text search.
    This searches inside Google Docs, PDFs, and text files.
    
    Args:
        query: The text to search for inside files
        max_files: Maximum number of results
    """
    logger = get_logger()
    logger.log_tool_call(
        tool_name="semantic_search",
        parameters={"query": query, "max_files": max_files}
    )
    try:
        service = get_drive_service()
        if not service:
            return "Error: Drive authentication required."
        
        # Use Drive API's fullText search
        # This is powerful and searches inside the file content
        drive_query = f"fullText contains '{query}' and trashed = false"
        
        results = service.files().list(
            pageSize=max_files,
            q=drive_query,
            fields="files(id, name, mimeType, webViewLink, size, modifiedTime)"
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            return f"No files found containing '{query}'"
        
        output = [f"Content Search Results for: '{query}'\n"]
        for i, file in enumerate(files, 1):
            output.append(f"{i}. {file['name']}")
            output.append(f"   ID: {file['id']}")
            output.append(f"   Type: {file['mimeType']}")
            output.append(f"   Link: {file.get('webViewLink', 'N/A')}\n")
            
        logger.log_tool_call(
            tool_name="semantic_search",
            parameters={"query": query},
            result=f"Found {len(files)} files"
        )
        return "\n".join(output)
    except Exception as e:
        logger.log_error(
            error_type="drive_semantic_search_error",
            error_message=str(e),
            context="semantic_search"
        )
        return f"Error in content search: {e}"

@mcp.tool()
def read_text_file(file_id: str) -> str:
    """
    Read the contents of a text file from Google Drive.
    
    Args:
        file_id: ID of the file to read
    """
    try:
        service = get_drive_service()
        if not service:
            return "Error: Drive authentication required."
        
        # Get file metadata to check mimeType
        file_metadata = service.files().get(fileId=file_id, fields='name,mimeType').execute()
        mime_type = file_metadata['mimeType']
        
        if mime_type != 'text/plain':
            return "Error: File is not a plain text file."
        
        # Download file content as text
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        fh.seek(0)
        content = fh.read().decode('utf-8')
        
        return content
    
    except Exception as e:
        return f"Error reading text file: {e}"

# NEW TOOL: Read contents of PDF, Google Doc, or text file
@mcp.tool()
def read_document(file_id: str) -> str:
    """
    Read the contents of a PDF, Google Doc, or plain text file from Google Drive and return the extracted text.
    
    Args:
        file_id: ID of the file to read
    """
    logger = get_logger()
    logger.log_tool_call(
        tool_name="read_document",
        parameters={"file_id": file_id}
    )
    try:
        service = get_drive_service()
        if not service:
            return "Error: Drive authentication required."
        
        # Get file metadata to check mimeType
        file_metadata = service.files().get(fileId=file_id, fields='name,mimeType').execute()
        mime_type = file_metadata['mimeType']
        
        fh = io.BytesIO()
        
        if mime_type == 'application/vnd.google-apps.document':
            # Export Google Doc to plain text
            request = service.files().export_media(fileId=file_id, mimeType='text/plain')
        elif mime_type in ['application/pdf', 'text/plain']:
            # Download binary content for PDF or text
            request = service.files().get_media(fileId=file_id)
        else:
            return "Error: Unsupported file type. Supported: Google Docs, PDF, plain text."
        
        # Download/export the content
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        fh.seek(0)
        
        if mime_type == 'application/pdf':
            # Extract text from PDF
            reader = PdfReader(fh)
            content = ""
            for page in reader.pages:
                content += page.extract_text() + "\n"
            return content.strip()
        else:
            # For text or exported Google Doc
            content = fh.read().decode('utf-8')
            return content.strip()
    
    except Exception as e:
        logger.log_error(
            error_type="drive_read_document_error",
            error_message=str(e),
            context="read_document"
        )
        return f"Error reading document: {e}"

# Tool definitions for Gemini integration
if __name__ == "__main__":
    print("Google Drive Agent - Available Functions:")
    print("1. list_files(max_results, query)")
    print("2. search_files(search_term, use_semantic)")
    print("3. download_file(file_id, destination)")
    print("4. upload_file(filepath, folder_id)")
    print("5. semantic_search(query, max_files)")
    print("6. read_text_file(file_id)")
    # NEW: Add to the list
    print("7. read_document(file_id)")