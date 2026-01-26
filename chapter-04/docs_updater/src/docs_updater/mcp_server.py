#!/usr/bin/env python
"""MCP Server for Documentation Updater Crew.

This server exposes:
- Tool: update_docs - invoke CrewAI to update documentation
- Resources: docs://{page} - documentation pages from docs.json
- Prompt: update-docs - user-invokable command for updating docs
"""
import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Thread pool for running sync code (Playwright) outside asyncio loop
_executor = ThreadPoolExecutor(max_workers=1)

# Initialize FastMCP server
mcp = FastMCP("docs-updater")


def get_docs_path() -> str:
    """Get the documentation directory path from environment or default."""
    return os.environ.get("DOCS_PATH", "./docs")


def get_doc_pages() -> list[str]:
    """Parse docs.json to get list of documentation pages."""
    docs_path = get_docs_path()
    docs_json_path = Path(docs_path) / "docs.json"

    if not docs_json_path.exists():
        return []

    with open(docs_json_path) as f:
        config = json.load(f)

    pages = []
    # Handle navigation structure from Mintlify docs.json
    navigation = config.get("navigation", {})

    # Handle tabs-based navigation
    for tab in navigation.get("tabs", []):
        for group in tab.get("groups", []):
            pages.extend(group.get("pages", []))

    # Handle direct groups (no tabs)
    for group in navigation.get("groups", []):
        pages.extend(group.get("pages", []))

    return pages


# =============================================================================
# TOOL: update_docs
# =============================================================================
def _run_crew_sync(changes_description: str, docs_path: str) -> str:
    """Run the crew synchronously (called from thread pool)."""
    from docs_updater.crew import DocsUpdater
    from docs_updater.tools.browser_tools import close_browser

    try:
        # verbose=False to avoid rich output corrupting MCP's stdio JSON protocol
        result = DocsUpdater(docs_base_directory=docs_path, verbose=False).crew().kickoff(
            inputs={"latest_changes": changes_description}
        )
        return str(result)
    finally:
        close_browser()


@mcp.tool()
async def update_docs(changes_description: str) -> str:
    """
    Update documentation based on a description of what changed in the app.

    This tool invokes the DocsUpdater CrewAI crew which will:
    1. Update relevant documentation files based on the changes
    2. Take new screenshots if needed

    Args:
        changes_description: Detailed description of what changed in the application.
            Be specific about UI changes, feature additions/removals, etc.

    Returns:
        Summary of documentation updates performed and screenshots taken.
    """
    docs_path = get_docs_path()

    # Run sync crew code in thread pool to avoid blocking asyncio
    # and to allow Playwright sync API to work
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _executor,
        _run_crew_sync,
        changes_description,
        docs_path
    )
    return result


# =============================================================================
# RESOURCES: docs://{page_name}
# =============================================================================
@mcp.resource("docs://{page_name}")
def read_doc_page(page_name: str) -> str:
    """
    Read a documentation page by name.

    Available pages are defined in docs.json navigation.

    Args:
        page_name: The page name (without extension), e.g., "introduction",
            "getting-started", "dashboard-overview"

    Returns:
        The content of the documentation page in MDX/Markdown format.
    """
    docs_path = get_docs_path()

    # Try .mdx first, then .md
    for ext in [".mdx", ".md"]:
        file_path = Path(docs_path) / f"{page_name}{ext}"
        if file_path.exists():
            return file_path.read_text()

    # Check if there's a nested path (e.g., "guides/intro")
    for ext in [".mdx", ".md"]:
        file_path = Path(docs_path) / f"{page_name}{ext}"
        if file_path.exists():
            return file_path.read_text()

    available = get_doc_pages()
    return f"Page '{page_name}' not found. Available pages: {', '.join(available)}"


# =============================================================================
# PROMPT: update-docs
# =============================================================================
@mcp.prompt()
def update_docs_prompt(changes: str = "") -> str:
    """
    Prompt to update documentation based on application changes.

    Use this as a slash command (/update-docs) in Cursor to trigger
    documentation updates after making code changes.

    Args:
        changes: Description of what changed in the application.
            If empty, you'll be prompted to describe the changes.
    """
    # Get list of current doc pages for context
    pages = get_doc_pages()
    pages_list = "\n".join(f"- docs://{p}" for p in pages) if pages else "No pages found"

    changes_section = changes if changes else "[Please describe what changed in the application]"

    return f"""You are helping update documentation for an application.

## Current Documentation Pages (available as resources)
{pages_list}

## Changes to Document
{changes_section}

## Instructions
1. First, read the relevant documentation pages using the docs:// resources above
2. Understand what documentation needs to be updated based on the changes
3. Use the update_docs tool with a detailed description of the changes
4. Report what was updated

Please proceed with updating the documentation based on the changes described above.
"""


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
