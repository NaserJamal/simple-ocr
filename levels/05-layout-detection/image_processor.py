"""
Image preprocessing module for layout detection
Handles PDF to image conversion with proper resizing for VLM accuracy
"""

import io
import base64
import pymupdf
from PIL import Image
from typing import Tuple
import logging

from config import TARGET_SIZE, RENDER_SCALE

log = logging.getLogger(__name__)


class ImageProcessor:
    """Processes PDF pages into properly sized images for VLM analysis"""

    def __init__(self, target_size: int = TARGET_SIZE):
        """
        Initialize image processor

        Args:
            target_size: Target size for the processed image (will be square canvas)
        """
        self.target_size = target_size

    def process_page(self, page: pymupdf.Page) -> Tuple[str, float, float, float, float]:
        """
        Convert PDF page to base64-encoded image with proper resizing

        Args:
            page: PyMuPDF page object

        Returns:
            Tuple of (base64_image, original_width, original_height, scale_x, scale_y)
        """
        try:
            pix = page.get_pixmap(
                matrix=pymupdf.Matrix(RENDER_SCALE, RENDER_SCALE),
                colorspace=pymupdf.csRGB,
                alpha=False
            )

            original_width = float(pix.width)
            original_height = float(pix.height)

            img_bytes = pix.tobytes("png")
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

            max_edge = max(pil_img.width, pil_img.height)
            scale = self.target_size / max_edge if max_edge > 0 else 1.0

            resized_width = int(round(pil_img.width * scale))
            resized_height = int(round(pil_img.height * scale))
            resized_img = pil_img.resize((resized_width, resized_height), Image.LANCZOS)

            canvas = Image.new("RGB", (self.target_size, self.target_size), (255, 255, 255))
            canvas.paste(resized_img, (0, 0))

            buffer = io.BytesIO()
            canvas.save(buffer, format="PNG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            log.info(f"Processed page: {int(original_width)}x{int(original_height)} -> {resized_width}x{resized_height} (scale={scale:.3f})")

            return img_base64, original_width, original_height, scale, scale

        except Exception as e:
            log.error(f"Failed to process page: {e}")
            raise

    def denormalize_coordinates(
        self,
        rect: list,
        original_width: float,
        original_height: float,
        scale_x: float,
        scale_y: float
    ) -> Tuple[float, float, float, float]:
        """Convert padded image coordinates back to original pixel space"""
        try:
            x0, y0, x1, y1 = [float(v) for v in rect]

            back_scale_x = 1.0 / scale_x if scale_x else 1.0
            back_scale_y = 1.0 / scale_y if scale_y else 1.0

            x0, x1 = sorted([x0 * back_scale_x, x1 * back_scale_x])
            y0, y1 = sorted([y0 * back_scale_y, y1 * back_scale_y])

            return (
                max(0.0, min(original_width, x0)),
                max(0.0, min(original_height, y0)),
                max(0.0, min(original_width, x1)),
                max(0.0, min(original_height, y1))
            )

        except (TypeError, ValueError) as e:
            log.error(f"Failed to denormalize coordinates: {e}")
            raise
