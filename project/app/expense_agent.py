"""
Expense Agent for Reimbursement Validation
Uses Gemini to validate a receipt PDF against a fixed expense policy.
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai
import fitz  # PyMuPDF for PDF text extraction
from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Expense Agent")
load_dotenv()

# Configure Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    print("Warning: GEMINI_API_KEY not set.")

AI_MODEL = "gemini-2.5-flash"

# Fixed policy text (loaded from Expense Policy.txt)
# Assuming Expense Policy.txt is in the same directory; adjust path if needed
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
POLICY_PATH = os.path.join(SCRIPT_DIR, "Expense Policy.txt")

with open(POLICY_PATH, "r", encoding="utf-8") as f:
    POLICY_TEXT = f.read()

def read_pdf_text(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    if not os.path.exists(pdf_path):
        return "Error: Receipt file not found."
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

@mcp.tool()
def validate_reimbursement(receipt_path: str) -> str:
    """
    Validate a reimbursement request based on the uploaded receipt PDF against the fixed expense policy.
    Returns only 'APPROVED' or 'DENIED'.
    
    Args:
        receipt_path: Local path to the receipt PDF.
    """
    receipt_text = read_pdf_text(receipt_path)
    if receipt_text.startswith("Error"):
        return "DENIED"  # No receipt, no reimbursement

    # Step 1: Extract receipt date
    date_prompt = f"""
    Extract only the receipt date from the following text.
    Return the date in ISO format (YYYY-MM-DD) if possible.
    If no date is found, reply with 'UNKNOWN'.

    Receipt text:
    {receipt_text}
    """

    model = genai.GenerativeModel(AI_MODEL)
    date_response = model.generate_content(date_prompt)
    receipt_date_str = date_response.text.strip()

    # Step 2: Compute days since receipt
    analysis_date = datetime.now()
    days_since_receipt = None
    receipt_date = None

    try:
        if receipt_date_str != "UNKNOWN":
            receipt_date = datetime.strptime(receipt_date_str, "%Y-%m-%d")
            days_since_receipt = (analysis_date - receipt_date).days
    except Exception:
        pass  # If parsing fails, treat as UNKNOWN

    # Step 3: Build main prompt
    current_date = analysis_date.strftime("%Y-%m-%d")
    main_prompt = f"""
    You are an expense auditor.
    Date of analysis: {current_date}

    Here is the company policy document:
    {POLICY_TEXT}

    Here is the receipt with expenses:
    {receipt_text}
    """

    if receipt_date:
        main_prompt += f"""
        The receipt is dated {receipt_date_str}, which is {days_since_receipt} days ago.
        """

    main_prompt += """
    Task: Determine if the reimbursement for the item(s) in the receipt should be granted based on the policy, including date constraints (e.g., must be within 30 days), eligible items, price limits, and non-reimbursable items.
    Output only 'APPROVED' or 'DENIED'. If any part violates the policy (e.g., date too old, item not eligible, over $100), output 'DENIED'.
    """

    # Call Gemini
    response = model.generate_content(main_prompt)
    result = response.text.strip().upper()
    
    # Ensure output is strictly APPROVED or DENIED
    if result not in ["APPROVED", "DENIED"]:
        return "DENIED"  # Default to denied if unclear
    
    return result

if __name__ == "__main__":
    print("Expense Agent - Available Functions:")
    print("1. validate_reimbursement(receipt_path)")