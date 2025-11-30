"""
Demo script for Google Drive Agent
Tests file operations and RAG capabilities
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))
import drive_agent

from drive_agent import (
    list_files,
    search_files,
    download_file,
    upload_file,
    semantic_search
)

def run_demo():
    print("🚀 Google Drive Agent Demo\n")
    
    # 1. List Files
    print("--- 1. Listing Files ---")
    print(list_files(max_results=5))
    print("\n")
    
    # 2. Upload a Test File
    print("--- 2. Uploading Test File ---")
    with open("demo_test.txt", "w") as f:
        f.write("This is a demo file for the Google Drive Agent.\nIt contains some sample text to verify content search.")
    
    print(upload_file("demo_test.txt"))
    print("\n")
    
    # 3. Search Files (Name)
    print("--- 3. Searching Files (by Name) ---")
    print(search_files("demo_test"))
    print("\n")
    
    # 4. Content Search (Native)
    print("--- 4. Content Search (Native) ---")
    print("Searching for 'sample text' inside files...")
    # Note: It might take a few seconds for Drive to index the new file
    import time
    time.sleep(5) 
    print(semantic_search("sample text"))
    print("\n")
    
    # Clean up
    import os
    if os.path.exists("demo_test.txt"):
        os.remove("demo_test.txt")
    
    print("✅ Demo complete!")

if __name__ == "__main__":
    run_demo()
