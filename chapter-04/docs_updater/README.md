# Chapter 4: Agent Delegation with MCP Browser Automation

This example demonstrates agent delegation in CrewAI, where a documentation writer delegates screenshot tasks to a browser automation specialist powered by Playwright MCP.

## What It Does

Two agents collaborate to keep documentation in sync with application changes:
1. **Documentation Writer** - Reviews and updates Mintlify documentation files
2. **Screenshot Specialist** - Captures application screenshots using browser automation

When the documentation writer identifies screenshots that need updating, it delegates the task to the screenshot specialist, who navigates the web app, logs in, and captures the required screenshots.

## Key Concepts

- **Agent Delegation**: `allow_delegation=True` enables agents to delegate work to coworkers
- **MCP Integration**: Uses `MCPServerAdapter` with `@playwright/mcp` for browser automation
- **Scoped File Tools**: Secure file operations restricted to the docs directory
- **Tool Handoff**: Screenshot paths are passed back so the writer can copy them to docs

## Prerequisites

- Node.js (for Playwright MCP server)
- A running web application at `http://localhost:4100` (demo-app provided)

### mcpadapt Compatibility

This example requires a fix to the `mcpadapt` library for OpenAI schema validation. See [PR #80](https://github.com/grll/mcpadapt/pull/80) for details.

The fix removes extra `Field()` kwargs that caused invalid JSON schemas with `None` values, which OpenAI's API rejects.

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Set environment variables in `.env`:
   ```
   OPENAI_API_KEY=your_key
   ```

3. Start the demo application:
   ```bash
   cd ../demo-app
   npm install
   npm run dev
   ```

## Running

```bash
DOCS_PATH=/path/to/demo-docs uv run docs_updater
```

The crew will:
1. Read the documentation files
2. Identify changes needed based on `latest_changes` input
3. Delegate screenshot capture to the specialist
4. Copy captured screenshots to the docs folder

## Files

- `src/docs_updater/crew.py` - Crew with MCP adapter setup and agent delegation
- `src/docs_updater/config/agents.yaml` - Agent definitions with Playwright MCP workflow
- `src/docs_updater/config/tasks.yaml` - Task with delegation instructions
- `src/docs_updater/tools/scoped_file_tools.py` - Secure file tools for docs directory

## Architecture

```
┌─────────────────────┐
│ Documentation Writer│
│  (allow_delegation) │
└──────────┬──────────┘
           │ delegates
           ▼
┌─────────────────────┐     ┌─────────────────┐
│Screenshot Specialist│────▶│ Playwright MCP  │
│                     │     │ (browser tools) │
└─────────────────────┘     └─────────────────┘
```
