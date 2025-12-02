#!/bin/bash

# Start script for running both MCP server and UI app

# Start the MCP server in the background
echo "Starting MCP server..."
python gemini_mcp.py &
MCP_PID=$!

# Wait a few seconds for MCP to start
sleep 5

# Start the UI app in the foreground
echo "Starting UI app..."
python ui_app.py

# If UI app exits, kill the MCP server
# kill $MCP_PID
