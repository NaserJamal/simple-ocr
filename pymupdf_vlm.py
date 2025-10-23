import pymupdf
import os
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client with custom endpoint
client = OpenAI(
    api_key=os.getenv("OCR_MODEL_API_KEY"),
    base_url=os.getenv("OCR_MODEL_BASE_URL")
)

doc = pymupdf.open("PDF/1-page-text-img.pdf")
output = []

for i, page in enumerate(doc, 1):
    # Check if page has images
    images = page.get_images()
    has_images = len(images) > 0

    # Extract text with PyMuPDF
    text = page.get_text().strip()

    # Decide: if page has images, send to VLM; otherwise use PyMuPDF text
    if has_images:
        print(f"Page {i}: Found {len(images)} image(s) - Sending to VLM")

        # Convert page to image
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.pil_tobytes(format="PNG")
        img_b64 = base64.b64encode(img_bytes).decode()

        # Send to VLM for OCR
        response = client.chat.completions.create(
            model=os.getenv("OCR_MODEL_NAME"),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all text from this image."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                ]
            }]
        )
        output.append(response.choices[0].message.content)
    else:
        print(f"Page {i}: No images - Using PyMuPDF text ({len(text)} chars)")
        output.append(text)

open("output.txt", "w").write("\n".join(output))
