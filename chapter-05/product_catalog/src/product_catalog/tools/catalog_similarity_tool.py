import json
import os
from pathlib import Path

import chromadb
import numpy as np
from crewai.tools import BaseTool
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

EMBEDDING_MODEL = "gemini-embedding-2-preview"
EMBEDDING_DIMS = 768
# Resolve INDEX_PATH against the project root so the tool works regardless of CWD.
# This file lives at <project_root>/src/product_catalog/tools/catalog_similarity_tool.py
PROJECT_ROOT = Path(__file__).resolve().parents[3]
INDEX_PATH = str(PROJECT_ROOT / "data" / "catalog_index")


class CatalogSimilarityInput(BaseModel):
    image_path: str = Field(description="Path to the product image file")
    product_description: str = Field(description="Text description of the product")
    top_k: int = Field(default=5, description="Number of similar products to return")


class CatalogSimilarityTool(BaseTool):
    name: str = "Catalog Similarity Search"
    description: str = (
        "Find similar products in the existing catalog using multimodal "
        "embeddings. Provide a product image path and text description to "
        "find the most similar existing products with similarity scores."
    )
    args_schema: type[BaseModel] = CatalogSimilarityInput

    def _run(self, image_path: str, product_description: str, top_k: int = 5) -> str:
        try:
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                return (
                    "Error: GOOGLE_API_KEY is not set. Add it to your environment "
                    "or .env file and try again."
                )

            if not os.path.isfile(image_path):
                return f"Error: Image file not found at '{image_path}'."

            if not os.path.isdir(INDEX_PATH):
                return (
                    f"Error: Catalog index not found at '{INDEX_PATH}'. "
                    "Run `uv run build_index` to create it first."
                )

            client = genai.Client(api_key=api_key)

            with open(image_path, "rb") as f:
                image_bytes = f.read()

            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=[
                    types.Content(
                        parts=[
                            types.Part(text=product_description),
                            types.Part.from_bytes(
                                data=image_bytes, mime_type="image/jpeg"
                            ),
                        ]
                    )
                ],
                config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMS),
            )

            if not result.embeddings:
                return "Error: Gemini returned no embeddings for the input."

            embedding = np.array(result.embeddings[0].values)
            norm = np.linalg.norm(embedding)
            if norm == 0:
                return "Error: Received a zero-norm embedding from Gemini; cannot search."
            embedding = (embedding / norm).tolist()

            db = chromadb.PersistentClient(path=INDEX_PATH)
            collection = db.get_collection("products")

            results = collection.query(query_embeddings=[embedding], n_results=top_k)

            similar = []
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                similar.append(
                    {
                        "title": metadata["title"],
                        "price": metadata["price"],
                        "category": metadata["category"],
                        "description": metadata["description"],
                        "similarity_score": round(1 - distance, 3),
                    }
                )

            return json.dumps(similar, indent=2)
        except Exception as e:
            return f"Error searching catalog: {type(e).__name__}: {e}"
