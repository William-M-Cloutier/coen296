# Logging Integration for Individual Agents

## expense_agent.py

### 1. Add import (after line 10):
```python
from logging_utils import get_logger
```

### 2. In `validate_reimbursement` function, add at the beginning (after line 51):
```python
    logger = get_logger()
    logger.log_tool_call(
        tool_name="validate_reimbursement",
        parameters={"receipt_path": receipt_path}
    )
```

### 3. After date extraction (after line 68):
```python
    logger.log_model_response(
        model_name=f"{AI_MODEL} (expense_date_extraction)",
        prompt=date_prompt,
        response=receipt_date_str,
        thinking_trace="Extracting receipt date from PDF text"
    )
```

### 4. After final validation (replace lines 106-113):
```python
    # Call Gemini
    response = model.generate_content(main_prompt)
    result = response.text.strip().upper()
    
    logger. log_model_response(
        model_name=f"{AI_MODEL} (expense_validation)",
        prompt=main_prompt,
        response=result,
        thinking_trace=f"Validating reimbursement against policy. Receipt date: {receipt_date_str if receipt_date else 'UNKNOWN'}, Days since: {days_since_receipt if days_since_receipt else 'N/A'}"
    )
    
    # Ensure output is strictly APPROVED or DENIED
    if result not in ["APPROVED", "DENIED"]:
        logger.log_error(
            error_type="expense_validation_unclear",
            error_message=f"Model returned unclear result: {result}",
            context="validate_reimbursement"
        )
        return "DENIED"  # Default to denied if unclear
    
    logger.log_tool_call(
        tool_name="validate_reimbursement",
        parameters={"receipt_path": receipt_path},
        result=result
    )
    
    return result
```

---

## gmail_agent.py

Since Gmail agent doesn't use Gemini (it uses Gmail API directly), we'll log the operations:

### 1. Add import (after line 11):
```python
from logging_utils import get_logger
```

### 2. In each tool function, add logging:

#### For `send_email` (after line 125):
```python
def send_email(to: str, subject: str, body: str) -> str:
    logger = get_logger()
    logger.log_tool_call(
        tool_name="send_email",
        parameters={"to": to, "subject": subject, "body_preview": body[:100]  + "..."}
    )
    try:
        # ... existing code ...
        send_message = (service.users().messages().send(userId="me", body=create_message).execute())
        result = f"Email sent successfully! Message Id: {send_message['id']}"
        logger.log_tool_call(
            tool_name="send_email",
            parameters={"to": to,"subject": subject},
            result=result
        )
        return result
    except Exception as e:
        logger.log_error(
            error_type="gmail_send_error",
            error_message=str(e),
            context="send_email"
        )
        # ... rest of error handling
```

**Similar pattern for other functions:**
- `list_emails`: Log parameters and results
- `read_email`: Log message_id and result preview
- `create_label`: Log label creation
- `apply_label`: Log label application

---

## drive_agent.py

Similar to Gmail agent, Drive agent uses Google Drive API directly:

### 1. Add import (after line 15):
```python
from logging_utils import get_logger
```

### 2. Add logging to key operations:

#### For `semantic_search` (after line 195):
```python
def semantic_search(query: str, max_files: int = 10) -> str:
    logger = get_logger()
    logger.log_tool_call(
        tool_name="semantic_search",
        parameters={"query": query, "max_files": max_files}
    )
    try:
        # ... existing code ...
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
```

**Similar pattern for:**
- `upload_file`: Log file uploads
- `download_file`: Log file downloads
- `list_files`: Log file listing operations
- `read_document`: Log document reading with file info

---

## Quick Integration Summary

For **all three agents**, the pattern is:
1. Add `from logging_utils import get_logger` at the top
2. At the start of each tool function: `logger = get_logger()`
3. Log tool calls with parameters
4. Log results (especially for Gemini calls in expense_agent)
5. Log errors in exception handlers

This will capture the complete thinking trace when the orchestration agent calls these agents!
