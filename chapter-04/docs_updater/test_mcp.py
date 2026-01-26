#!/usr/bin/env python3
"""Test script to verify Playwright MCP tools are loading correctly."""

import os
from mcp import StdioServerParameters
from crewai_tools import MCPServerAdapter

def test_mcp_connection():
    print("Testing Playwright MCP connection...")
    print("-" * 50)

    server_params = StdioServerParameters(
        command="npx",
        args=["@playwright/mcp@latest"],
        env=os.environ.copy(),
    )

    try:
        print("Connecting to MCP server (this may take a moment)...")

        with MCPServerAdapter(server_params, connect_timeout=60) as tools:
            print(f"\n✅ Successfully connected! Found {len(tools)} tools:\n")
            for tool in tools:
                desc = tool.description[:60] if tool.description else "No description"
                print(f"  - {tool.name}: {desc}...")

    except Exception as e:
        print(f"\n❌ Failed to connect to MCP server:")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mcp_connection()
