"""
Image preprocessing module for template-based parsing
Handles PDF/image conversion with proper resizing for VLM accuracy
"""

import io
import base64
import pymupdf
from PIL import Image
from pathlib import Path
from typing import Tuple

from config import TARGET_SIZE, RENDER_SCALE


class ImageProcessor:
    """Processes PDF pages and images into properly sized images for VLM analysis"""

    def __init__(self, target_size: int = TARGET_SIZE):
        """
        Initialize image processor

        Args:
            target_size: Target size for the processed image (will be square canvas)
        """
        self.target_size = target_size

    def process_pdf_page(self, page: pymupdf.Page) -> str:
        """
        Convert PDF page to base64-encoded image with proper resizing

        Args:
            page: PyMuPDF page object

        Returns:
            Base64-encoded PNG image
        """
        # Render PDF page to pixmap
        pix = page.get_pixmap(
            matrix=pymupdf.Matrix(RENDER_SCALE, RENDER_SCALE),
            colorspace=pymupdf.csRGB,
            alpha=False
        )

        # Convert to PIL Image
        img_bytes = pix.tobytes("png")
        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        # Resize and pad
        return self._resize_and_encode(pil_img)

    def process_image_file(self, file_path: str) -> str:
        """
        Process an image file with proper resizing

        Args:
            file_path: Path to image file

        Returns:
            Base64-encoded PNG image
        """
        pil_img = Image.open(file_path).convert("RGB")
        return self._resize_and_encode(pil_img)

    def _resize_and_encode(self, pil_img: Image.Image) -> str:
        """
        Resize image to target size with padding and encode to base64

        Args:
            pil_img: PIL Image object

        Returns:
            Base64-encoded PNG image
        """
        # Calculate scale to fit within target size
        max_edge = max(pil_img.width, pil_img.height)
        scale = self.target_size / max_edge if max_edge > 0 else 1.0

        # Resize image maintaining aspect ratio
        resized_width = int(round(pil_img.width * scale))
        resized_height = int(round(pil_img.height * scale))
        resized_img = pil_img.resize((resized_width, resized_height), Image.LANCZOS)

        # Create white canvas and paste resized image
        canvas = Image.new("RGB", (self.target_size, self.target_size), (255, 255, 255))
        canvas.paste(resized_img, (0, 0))

        # Encode to base64
        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return img_base64

    def process_file(self, file_path: str) -> str:
        """
        Process any file (PDF or image) with proper resizing

        Args:
            file_path: Path to file (PDF, PNG, JPG, etc.)

        Returns:
            Base64-encoded PNG image
        """
        file_path = Path(file_path)

        # Handle PDF files
        if file_path.suffix.lower() == '.pdf':
            doc = pymupdf.open(file_path)
            page = doc[0]  # Process first page
            result = self.process_pdf_page(page)
            doc.close()
            return result

        # Handle image files
        else:
            return self.process_image_file(str(file_path))
