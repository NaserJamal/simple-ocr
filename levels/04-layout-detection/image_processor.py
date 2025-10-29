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

        This method:
        1. Renders the PDF page at 1:1 scale (72 DPI)
        2. Resizes to fit within target_size while maintaining aspect ratio
        3. Places on square white canvas to avoid VLM preprocessing distortion

        Args:
            page: PyMuPDF page object

        Returns:
            Tuple of:
                - base64 encoded PNG image string
                - original image width (before padding)
                - original image height (before padding)
                - scale factor used for resizing (original -> resized)
                - scale factor used for resizing (original -> resized)
        """
        try:
            # Render page at 1:1 resolution (72 DPI)
            # This gives us direct pixel-to-PDF-point mapping
            pix = page.get_pixmap(
                matrix=pymupdf.Matrix(RENDER_SCALE, RENDER_SCALE),
                colorspace=pymupdf.csRGB,
                alpha=False
            )

            # Store original dimensions
            original_width = float(pix.width)
            original_height = float(pix.height)

            # Convert to PIL Image
            img_bytes = pix.tobytes("png")
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

            # Calculate scale to fit within target size
            max_edge = max(pil_img.width, pil_img.height)
            scale = self.target_size / max_edge if max_edge > 0 else 1.0

            # Resize image maintaining aspect ratio
            resized_width = int(round(pil_img.width * scale))
            resized_height = int(round(pil_img.height * scale))
            resized_img = pil_img.resize((resized_width, resized_height), Image.LANCZOS)

            # Create square white canvas and place resized image at top-left
            canvas = Image.new("RGB", (self.target_size, self.target_size), (255, 255, 255))
            canvas.paste(resized_img, (0, 0))

            # Encode to base64
            buffer = io.BytesIO()
            canvas.save(buffer, format="PNG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            log.info(
                f"Processed page: {original_width}x{original_height} -> "
                f"{resized_width}x{resized_height} (scale={scale:.3f})"
            )

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
        """
        Convert normalized/padded coordinates back to original image space

        Args:
            rect: Bounding box [x0, y0, x1, y1] in padded image coordinates
            original_width: Original image width before padding
            original_height: Original image height before padding
            scale_x: Scale factor applied to width
            scale_y: Scale factor applied to height

        Returns:
            Tuple of (x0, y0, x1, y1) in original image pixel coordinates
        """
        try:
            x0_norm, y0_norm, x1_norm, y1_norm = [float(v) for v in rect]

            # Reverse the scaling (padded space -> resized space -> original space)
            back_scale_x = 1.0 / scale_x if scale_x else 1.0
            back_scale_y = 1.0 / scale_y if scale_y else 1.0

            x0 = x0_norm * back_scale_x
            y0 = y0_norm * back_scale_y
            x1 = x1_norm * back_scale_x
            y1 = y1_norm * back_scale_y

            # Ensure proper ordering
            x_min, x_max = sorted([x0, x1])
            y_min, y_max = sorted([y0, y1])

            # Clamp to original image bounds
            x_min = max(0.0, min(original_width, x_min))
            x_max = max(0.0, min(original_width, x_max))
            y_min = max(0.0, min(original_height, y_min))
            y_max = max(0.0, min(original_height, y_max))

            return x_min, y_min, x_max, y_max

        except (TypeError, ValueError) as e:
            log.error(f"Failed to denormalize coordinates: {e}")
            raise
