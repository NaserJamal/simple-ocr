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

from .config import TARGET_SIZE, RENDER_SCALE

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
        """Convert PDF page to base64-encoded image with proper resizing"""
        pix = page.get_pixmap(matrix=pymupdf.Matrix(RENDER_SCALE, RENDER_SCALE), colorspace=pymupdf.csRGB, alpha=False)
        original_width, original_height = float(pix.width), float(pix.height)

        pil_img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

        scale = self.target_size / max(pil_img.size)
        new_size = (int(round(pil_img.width * scale)), int(round(pil_img.height * scale)))
        resized_img = pil_img.resize(new_size, Image.LANCZOS)

        canvas = Image.new("RGB", (self.target_size, self.target_size), (255, 255, 255))
        canvas.paste(resized_img, (0, 0))

        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        log.info(f"Processed page: {int(original_width)}x{int(original_height)} -> {new_size[0]}x{new_size[1]} (scale={scale:.3f})")
        return img_base64, original_width, original_height, scale, scale

    def denormalize_coordinates(
        self,
        rect: list,
        original_width: float,
        original_height: float,
        scale_x: float,
        scale_y: float
    ) -> Tuple[float, float, float, float]:
        """Convert padded image coordinates back to original pixel space"""
        x0, y0, x1, y1 = [float(v) for v in rect]
        back_scale = 1.0 / scale_x if scale_x else 1.0

        x0, x1 = sorted([x0 * back_scale, x1 * back_scale])
        y0, y1 = sorted([y0 * back_scale, y1 * back_scale])

        return (
            max(0.0, min(original_width, x0)),
            max(0.0, min(original_height, y0)),
            max(0.0, min(original_width, x1)),
            max(0.0, min(original_height, y1))
        )
