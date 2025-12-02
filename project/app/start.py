"""
Start script for running both MCP server and UI app
Works on Windows and Unix systems
"""
import subprocess
import sys
import time
import os

# Set default MCP_URL if not provided
if "MCP_URL" not in os.environ:
    os.environ["MCP_URL"] = "http://127.0.0.1:8000/sse"

def start_services():
    print("="*60)
    print("Starting Orchestration Agent Multi-Service Deployment")
    print("="*60)
    
    print("\n[1/2] Starting MCP server on port 8000...")
    
    # Create a copy of environment variables
    mcp_env = os.environ.copy()
    
    # Force uvicorn (used by fastmcp) to use port 8000 and bind to 0.0.0.0
    # This overrides Render's PORT variable for the MCP process only
    mcp_env["PORT"] = "8000"
    mcp_env["HOST"] = "0.0.0.0"
    
    # Start MCP server as subprocess - let it output to console
    mcp_process = subprocess.Popen(
        [sys.executable, "gemini_mcp.py"],
        # Don't capture output - let it print to console for debugging
        stdout=None,
        stderr=None,
        env=mcp_env  # Pass the modified environment
    )
    
    # Wait for MCP server to initialize
    print("[1/2] Waiting 5 seconds for MCP server to initialize...")
    time.sleep(5)
    
    # Check if MCP server is still running
    if mcp_process.poll() is not None:
        print("\n" + "="*60)
        print("ERROR: MCP server failed to start!")
        print("="*60)
        print("Exit code:", mcp_process.returncode)
        print("\nPossible causes:")
        print("- Missing dependencies (check requirements.txt installed)")
        print("- Port 8000 already in use")
        print("- Missing environment variables (GEMINI_API_KEY)")
        print("\nCheck logs above for more details.")
        sys.exit(1)
    
    print("[1/2] ✓ MCP server started successfully (PID: {})".format(mcp_process.pid))
    print("\n[2/2] Starting UI app...")
    
    # Start UI app (this blocks)
    try:
        ui_process = subprocess.Popen(
            [sys.executable, "ui_app.py"],
            stdout=None,
            stderr=None
        )
        print("[2/2] ✓ UI app started (PID: {})".format(ui_process.pid))
        print("\n" + "="*60)
        print("Both services running!")
        print("MCP Server: http://localhost:8000")
        print("UI App: http://0.0.0.0:{}".format(os.environ.get('PORT', 8080)))
        print("="*60)
        print("\nPress Ctrl+C to stop both services.")
        
        # Wait for UI app to finish
        ui_process.wait()
        
    except KeyboardInterrupt:
        print("\n\nReceived shutdown signal...")
    except Exception as e:
        print("\n\nError running UI app:", e)
    # finally:
    #     # Cleanup: terminate MCP server
    #     print("\nShutting down services...")
    #     print("- Terminating MCP server...")
    #     mcp_process.terminate()
    #     try:
    #         mcp_process.wait(timeout=5)
    #         print("- MCP server stopped")
    #     except:
    #         print("- Force killing MCP server...")
    #         mcp_process.kill()
    #         mcp_process.wait()
    #     print("\n✓ All services stopped.\n")

if __name__ == "__main__":
    start_services()
