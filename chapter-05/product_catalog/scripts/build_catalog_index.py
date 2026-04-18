"""Build the product catalog index using Gemini Embedding 2 and ChromaDB."""

import json
import os
import sys
import time
from pathlib import Path

import chromadb
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Resolve paths against the project root so the script works regardless of CWD.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = PROJECT_ROOT / "sample_products" / "catalog"
INDEX_PATH = PROJECT_ROOT / "data" / "catalog_index"
EMBEDDING_MODEL = "gemini-embedding-2-preview"
EMBEDDING_DIMS = 768


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        sys.exit(
            "Error: GOOGLE_API_KEY is not set. Copy .env.example to .env and add "
            "your key, or export it in your shell."
        )

    client = genai.Client(api_key=api_key)

    with open(CATALOG_DIR / "catalog.json") as f:
        catalog = json.load(f)

    db = chromadb.PersistentClient(path=str(INDEX_PATH))

    collection = db.get_or_create_collection(
        "products", metadata={"hnsw:space": "cosine"}
    )

    existing_ids = set(collection.get()["ids"]) if collection.count() > 0 else set()

    for i, product in enumerate(catalog):
        if product["id"] in existing_ids:
            print(f"  Skipped (exists): {product['title']}")
            continue

        image_path = CATALOG_DIR / product["image"]
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        text = f"{product['title']}. {product['description']}"

        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=[
                types.Content(
                    parts=[
                        types.Part(text=text),
                        types.Part.from_bytes(
                            data=image_bytes, mime_type="image/jpeg"
                        ),
                    ]
                )
            ],
            config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMS),
        )

        embedding = np.array(result.embeddings[0].values)
        embedding = (embedding / np.linalg.norm(embedding)).tolist()

        collection.add(
            ids=[product["id"]],
            embeddings=[embedding],
            metadatas=[
                {
                    "title": product["title"],
                    "description": product["description"],
                    "price": product["price"],
                    "category": product["category"],
                }
            ],
        )

        print(f"  Indexed: {product['title']}")

        if i < len(catalog) - 1:
            time.sleep(1)

    print(f"\nDone — indexed {len(catalog)} products into {INDEX_PATH}")


if __name__ == "__main__":
    main()
