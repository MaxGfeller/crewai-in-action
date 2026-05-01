import sys
from pathlib import Path

from crewai_files import ImageFile
from dotenv import load_dotenv

from product_catalog.crew import ProductCatalogCrew

# Load environment variables from .env at the project root so the crew and tools
# can read GOOGLE_API_KEY without requiring the user to export it manually.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def run():
    image_path = sys.argv[1] if len(sys.argv) > 1 else "sample_products/new/sneaker-red.jpg"

    result = ProductCatalogCrew().crew().kickoff(
        inputs={"image_path": image_path},
        input_files={"product_image": ImageFile(source=image_path)},
    )

    listing = result.tasks_output[1].pydantic
    findings = result.tasks_output[2].pydantic

    print("\n=== Product Listing ===")
    print(listing.model_dump_json(indent=2))
    print("\n=== Catalog Findings ===")
    print(findings.model_dump_json(indent=2))


def build_index():
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, "scripts/build_catalog_index.py"],
        check=True,
    )
