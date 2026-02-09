# Chapter 2: Single Agent - Market Research Analyst

This example demonstrates how to create a single CrewAI agent that acts as a Market Research Analyst, generating comprehensive competitive intelligence reports.

## What It Does

The agent analyzes a product category (e.g., "electric bikes") and produces a structured report covering:
- Market snapshot and customer needs
- Competitive landscape and differentiators
- Pricing, packaging, and positioning insights

## Key Concepts

- **Single Agent**: No crew needed - just one agent with `agent.kickoff()`
- **Tool Integration**: Uses `SerperDevTool` and `SerperScrapeWebsiteTool` for web research
- **Structured Output**: Pydantic models define the expected report structure

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Set environment variables in `.env`:
   ```
   OPENAI_API_KEY=your_key
   SERPER_API_KEY=your_key
   ```

## Running

```bash
uv run python src/market_researcher/main.py
```

The agent will research the product category and output a structured market research report.

## Files

- `src/market_researcher/main.py` - Agent definition and execution
