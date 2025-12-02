"""
Start script for running both MCP server and UI app
Works on Windows and Unix systems
"""
import subprocess
import sys
import time
import os

def start_services():
    print("Starting MCP server...")
    # Start MCP server as subprocess
    mcp_process = subprocess.Popen(
        [sys.executable, "gemini_mcp.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for MCP server to initialize
    print("Waiting for MCP server to initialize...")
    time.sleep(5)
    
    # Check if MCP server is still running
    if mcp_process.poll() is not None:
        print("ERROR: MCP server failed to start!")
        stdout, stderr = mcp_process.communicate()
        print("STDOUT:", stdout.decode())
        print("STDERR:", stderr.decode())
        sys.exit(1)
    
    print("MCP server started successfully (PID: {})".format(mcp_process.pid))
    print("Starting UI app...")
    
    # Start UI app (this blocks)
    try:
        ui_process = subprocess.Popen(
            [sys.executable, "ui_app.py"],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        ui_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Cleanup: terminate MCP server
        print("Terminating MCP server...")
        mcp_process.terminate()
        mcp_process.wait()
        print("All services stopped.")

if __name__ == "__main__":
    start_services()
