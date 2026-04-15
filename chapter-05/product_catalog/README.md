# Product Catalog Manager

A multimodal CrewAI application that automates product catalog management for
e-commerce. Given a product photo, the crew analyzes the image, generates an
optimized listing, and finds similar products in the existing catalog.

## Agents

1. **Image Analyzer** — Uses a vision-capable LLM to extract product features
   from photos (colors, materials, dimensions, branding)
2. **Description Writer** — Generates SEO-optimized product listings from the
   image analysis
3. **Catalog Analyst** — Uses Gemini multimodal embeddings to find similar
   products in the catalog and suggest pricing/positioning

## Setup

```bash
# Install dependencies
uv sync

# Set your Google API key
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# Build the catalog index (one-time setup)
uv run build_index
```

## Usage

```bash
# Analyze the default sample product (red sneaker)
uv run product_catalog

# Analyze a specific product image
uv run product_catalog path/to/product.jpg
```

## How it works

The crew uses two forms of multimodality:

- **Generative**: The Image Analyzer agent receives the product photo via
  CrewAI's native file passing (`input_files`) and its vision-capable LLM
  (Gemini 3 Flash) analyzes the image directly.
- **Embeddings**: The Catalog Analyst uses Gemini Embedding 2 to embed the
  product image and description into a shared vector space, then searches a
  ChromaDB index for similar catalog items.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google AI API key (for Gemini LLM + embeddings) |
