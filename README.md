# CrewAI Book Examples

Example projects demonstrating various CrewAI concepts and patterns, organized by chapter.

## Chapters

### Chapter 2: Single Agent Basics
**Project:** `market_researcher`

A single-agent example demonstrating how to create a Market Research Analyst that generates competitive intelligence reports. Shows:
- Agent configuration with role, goal, and backstory
- Tool integration (SerperDevTool, SerperScrapeWebsiteTool)
- Structured output with Pydantic models

### Chapter 3: Multi-Agent Crews with Knowledge
**Project:** `seo_crew`

An SEO content pipeline with three agents working sequentially. Shows:
- Multi-agent collaboration (keyword researcher, topic researcher, blog writer)
- Knowledge sources (text files, JSON)
- Custom tools (image generation)
- Sequential task execution

### Chapter 4: Agent Delegation with MCP Tools
**Project:** `docs_updater`

A documentation maintenance crew that updates Mintlify docs and captures screenshots. Shows:
- Agent delegation (`allow_delegation=True`)
- MCP (Model Context Protocol) server integration via `MCPServerAdapter`
- Playwright browser automation for screenshots
- Scoped file tools for secure file operations

## Prerequisites

- Python 3.10-3.13
- [uv](https://docs.astral.sh/uv/) for dependency management
- API keys as needed (OpenAI, Serper, etc.)

## Getting Started

Each chapter project can be run independently:

```bash
cd chapter-XX/project_name
uv sync
uv run <command>
```

See individual chapter READMEs for specific instructions.
