from google import genai
from google.genai import types
from PIL import Image
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

prompt = "Create a picture of a nano banana dish in a fancy restaurant with a Gemini theme"

response = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents=[prompt],
    config=types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"]
    ),
)

parts = getattr(response, "parts", None) or response.candidates[0].content.parts

for part in parts:
    if part.text is not None:
        print(part.text)
    elif part.inline_data is not None:
        part.as_image().save("generated_image.png")
        print("Saved generated_image.png")
