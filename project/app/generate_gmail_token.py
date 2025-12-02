from gmail_agent import get_gmail_service

print("Starting Gmail Authentication Flow...")
print("A browser window should open. Please log in to your Google Account.")

try:
    service = get_gmail_service()
    print("\nSUCCESS! 'gmail_token.json' has been generated.")
    print("Please commit this file to your repository and push to Render.")
except Exception as e:
    print(f"\nError: {e}")
    print("Make sure you have 'credentials.json' (or 'drive_credentials.json') in this folder.")
