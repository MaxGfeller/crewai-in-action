import json
import os

import chromadb
import numpy as np
from crewai.tools import BaseTool
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

EMBEDDING_MODEL = "gemini-embedding-2-preview"
EMBEDDING_DIMS = 768
INDEX_PATH = "data/catalog_index"


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
        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

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

        embedding = np.array(result.embeddings[0].values)
        embedding = (embedding / np.linalg.norm(embedding)).tolist()

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
