#!/bin/bash
# Start Playwright MCP server with shared browser context
# This maintains browser state between tool calls

echo "Starting Playwright MCP server on http://localhost:8931..."
echo "Browser context will be shared across all connections."
echo "Press Ctrl+C to stop."
echo ""

npx @playwright/mcp@latest \
    --port 8931 \
    --shared-browser-context \
    --browser chrome
