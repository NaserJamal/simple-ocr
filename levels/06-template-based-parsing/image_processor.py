"""
Image preprocessing module for template-based parsing.
Handles PDF/image conversion with proper resizing for VLM accuracy.
"""

import io
import base64
import pymupdf
from PIL import Image
from pathlib import Path

from config import TARGET_SIZE, RENDER_SCALE


class ImageProcessor:
    """Processes PDF pages and images into properly sized images for VLM analysis."""

    def __init__(self, target_size: int = TARGET_SIZE):
        self.target_size = target_size

    def _resize_and_encode(self, img: Image.Image) -> str:
        """Resize image to target size with padding and encode to base64."""
        max_edge = max(img.size)
        scale = self.target_size / max_edge if max_edge > 0 else 1.0

        new_size = (int(round(img.width * scale)), int(round(img.height * scale)))
        resized_img = img.resize(new_size, Image.LANCZOS)

        canvas = Image.new("RGB", (self.target_size, self.target_size), (255, 255, 255))
        canvas.paste(resized_img, (0, 0))

        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def _process_pdf(self, file_path: Path) -> str:
        """Convert PDF first page to base64-encoded image."""
        with pymupdf.open(file_path) as doc:
            pix = doc[0].get_pixmap(
                matrix=pymupdf.Matrix(RENDER_SCALE, RENDER_SCALE),
                colorspace=pymupdf.csRGB,
                alpha=False
            )
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            return self._resize_and_encode(img)

    def _process_image(self, file_path: Path) -> str:
        """Process image file with proper resizing."""
        img = Image.open(file_path).convert("RGB")
        return self._resize_and_encode(img)

    def process_file(self, file_path: str) -> str:
        """Process any file (PDF or image) with proper resizing."""
        path = Path(file_path)

        if path.suffix.lower() == '.pdf':
            return self._process_pdf(path)
        return self._process_image(path)
