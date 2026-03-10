# Setting Up the MCP Server

Now that we have implemented our agents and assembled the crew responsible for updating documentation based on a description of what changed in the app, the next step is to expose this functionality through an MCP server. Doing so allows a coding agent—such as Cursor or Claude Code—to invoke the crew directly.

## Choosing FastMCP

For this implementation, we will use the FastMCP library, which is inspired by FastAPI and makes creating MCP servers as straightforward as creating API servers. While FastMCP started as a community project, it was adopted as the official MCP SDK for Python. Version 2.0 introduces significantly more advanced features and provides access to a broader range of MCP-specific functionality.

First, install FastMCP:

```bash
uv add "mcp[cli]"
```

## Server Architecture

As discussed earlier, an MCP server can expose three main capabilities: resources, tools, and prompts. Our documentation updater will make use of all three:

- **Resources** provide the client with contextual information about the existing documentation—specifically, what pages exist and what topics are already covered.
- **A tool** invokes the crew with inputs from the coding agent to update documentation.
- **A prompt** defines a `/update-docs` command that instructs the underlying LLM on how to structure the update request.

Create the file `src/docs_updater/mcp_server.py` and start with the imports and server initialization:

```python
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
```

The `FastMCP` constructor takes a server name that identifies this server to clients. We also create a thread pool executor—we'll explain why shortly.

## Configuration Helpers

The server needs to know where the documentation files live. We'll read this from an environment variable, with a sensible default:

```python
def get_docs_path() -> str:
    """Get the documentation directory path from environment or default."""
    return os.environ.get("DOCS_PATH", "./docs")
```

We also need a function to discover which documentation pages exist. Mintlify stores its navigation structure in a `docs.json` file. This function parses that file and extracts all page names:

```python
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
```

Mintlify's navigation can be organized either with tabs (for larger documentation sites) or with simple groups. This function handles both structures.

## Implementing the Tool

The core functionality of our MCP server is the `update_docs` tool. When invoked, it runs the entire documentation updater crew—including the screenshot agent that uses Playwright.

There's an important technical consideration here: MCP servers use `asyncio` for handling requests, but Playwright's synchronous API cannot run directly in an asyncio event loop. If we tried to call our crew directly from an async function, Playwright would fail with threading errors.

The solution is to run the crew in a separate thread using a thread pool executor:

```python
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
```

Notice that we set `verbose=False` when creating the crew. This is crucial: CrewAI's verbose mode uses Rich for colorful console output, which would corrupt the JSON-RPC messages that MCP sends over stdio. By disabling verbose output, we ensure clean communication between the server and client.

Now we can define the async tool that delegates to this synchronous function:

```python
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
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        _executor,
        _run_crew_sync,
        changes_description,
        docs_path
    )
    return result
```

The `@mcp.tool()` decorator registers this function as an MCP tool. FastMCP automatically extracts the function signature, type hints, and docstring to create the tool's schema and description—similar to how we defined tool schemas for our browser tools, but with less boilerplate.

## Implementing Resources

Resources in MCP provide read-only context that clients can fetch. For our documentation updater, we expose each documentation page as a resource. This allows the coding agent to read existing documentation before deciding what needs to be updated.

```python
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
```

The `@mcp.resource()` decorator uses a URI template with `{page_name}` as a parameter. When a client requests `docs://introduction`, FastMCP extracts "introduction" and passes it to the function. The function then looks for matching `.mdx` or `.md` files in the documentation directory.

If the page doesn't exist, we return a helpful error message listing available pages. This helps the LLM recover gracefully when it requests a non-existent page.

## Implementing the Prompt

Prompts in MCP are reusable templates that clients can present as user actions—typically slash commands. Our `/update-docs` prompt guides the LLM through the documentation update workflow:

```python
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
```

This prompt serves several purposes:

1. **Discovery**: It lists all available documentation pages as resources, helping the LLM understand what documentation exists.
2. **Context**: It includes the user's description of changes, or prompts them to provide one.
3. **Instructions**: It guides the LLM through a workflow—read existing docs, understand what needs updating, invoke the tool.

When a user types `/update-docs` in Cursor, this prompt is injected into the conversation, steering the LLM toward using our MCP server's capabilities correctly.

## Running the Server

Finally, we add the entry point that starts the MCP server:

```python
def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
```

The `mcp.run()` method starts the server using stdio transport by default—it reads JSON-RPC requests from stdin and writes responses to stdout. This is the transport mode that Cursor and Claude Desktop use for local MCP servers.

To make the server runnable as a command, add it to your `pyproject.toml`:

```toml
[project.scripts]
docs-updater-mcp = "docs_updater.mcp_server:main"
```

After installing the package (`uv pip install -e .`), you can run the server with:

```bash
docs-updater-mcp
```

However, you won't typically run the server manually. Instead, you'll configure Cursor or Claude Desktop to start it automatically—which we'll cover in the next section.

## Testing the Server

Before integrating with Cursor, you can test the server using the MCP CLI. First, make sure the `DOCS_PATH` environment variable points to your documentation directory:

```bash
export DOCS_PATH=/path/to/crewai-in-action/chapter-04/demo-docs
```

Then use the MCP inspector to interact with your server:

```bash
mcp dev src/docs_updater/mcp_server.py
```

This opens an interactive session where you can:
- List available tools with `tools/list`
- List resources with `resources/list`
- List prompts with `prompts/list`
- Read a resource with `resources/read`
- Call a tool with `tools/call`

This is invaluable for debugging your server before connecting it to an actual client.


