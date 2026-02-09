# Chapter 3: Multi-Agent SEO Content Pipeline

This example demonstrates a multi-agent CrewAI crew that creates SEO-optimized blog content through collaborative research and writing.

## What It Does

Three agents work sequentially to produce a blog post:
1. **Keyword Researcher** - Analyzes competitors to find high-value keywords
2. **Topic Researcher** - Selects a topic incorporating the best keywords
3. **Blog Post Writer** - Writes an engaging, SEO-optimized post with generated images

## Key Concepts

- **Multi-Agent Crew**: Three specialized agents with distinct roles
- **Sequential Process**: Tasks execute in order, each building on previous outputs
- **Knowledge Sources**: Crew has access to `about-us.md` and `competitors.json`
- **Custom Tools**: `ImageGenerationTool` creates images for the blog post

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

3. Create knowledge files:
   - `knowledge/about-us.md` - Company background
   - `knowledge/competitors.json` - Competitor URLs to analyze

## Running

```bash
uv run seo_crew
```

The crew will research keywords, select a topic, and write a blog post saved to `blog_post.md`.

## Files

- `src/seo_crew/crew.py` - Crew definition with agents, tasks, and knowledge config
- `src/seo_crew/config/agents.yaml` - Agent role definitions
- `src/seo_crew/config/tasks.yaml` - Task descriptions
- `src/seo_crew/tools/image_generation_tool.py` - Custom image generation tool
