#!/bin/bash

# 1. Start MCP Server in the background
# We explicitly set PORT=8000 and HOST=0.0.0.0 for this process only
# The '&' puts it in the background
echo "Starting MCP Server on port 8000..."
PORT=8000 HOST=0.0.0.0 python gemini_mcp.py &

# 2. Wait for it to initialize
echo "Waiting 5 seconds for MCP to start..."
sleep 5

# 3. Start UI App in the foreground
# This will use the Render-provided PORT automatically
echo "Starting UI App..."
python ui_app.py
