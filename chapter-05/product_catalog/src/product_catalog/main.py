import sys

from crewai_files import ImageFile

from product_catalog.crew import ProductCatalogCrew


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
