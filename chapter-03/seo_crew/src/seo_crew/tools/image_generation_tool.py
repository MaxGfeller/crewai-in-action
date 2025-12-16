from typing import Type, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import os
import replicate

class ImageGenerationToolInput(BaseModel):
    image_description: str = Field(..., description="Description of the image to generate.")

class ImageGenerationTool(BaseTool):
    name: str = "generate_image"
    description: str = (
        "Generate a custom image based on the description provided."
    )
    args_schema: Type[BaseModel] = ImageGenerationToolInput
    base_path: str = Field(default=".", description="Base path where images should be saved")

    def _run(self, image_description: str) -> str:
        outputs = replicate.run(
            "black-forest-labs/flux-dev-lora",
            input={
                "prompt": image_description + " retro_neon style",
                "num_outputs": 1,
                "aspect_ratio": "16:9",
                "image_quality": 1,
                "image_format": "jpg",
                "lora_weights": "https://civitai.com/api/download/models/747123"
            }
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = next(iter(outputs))
        filename = f"output_{timestamp}.jpg"
        filepath = os.path.join(self.base_path, filename)
        os.makedirs(self.base_path, exist_ok=True)
        with open(filepath, "wb") as file:
            file.write(output.read())

        return f"Image generated successfully: {filepath}"
