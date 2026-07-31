import os
import fal_client

# fal_client automatically reads the FAL_KEY environment variable --
# no need to pass it explicitly when creating a client object.
os.environ.setdefault("FAL_KEY", os.environ.get("FAL_API_KEY", ""))

MODEL = "fal-ai/flux/schnell"


def generate_image(prompt: str) -> str:
    """Calls fal.ai FLUX schnell, returns a hosted URL to the generated image."""
    result = fal_client.subscribe(
        MODEL,
        arguments={"prompt": prompt},
    )
    return result["images"][0]["url"]
