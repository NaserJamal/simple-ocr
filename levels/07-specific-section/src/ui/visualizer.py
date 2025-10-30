"""Visualization module for section detection results."""

import logging
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFont

from src.infrastructure.config import SECTION_COLORS, VIZ_ALPHA, VIZ_FONT_SIZE, VIZ_LINE_WIDTH

log = logging.getLogger(__name__)


class SectionVisualizer:
    """Visualizes detected layout sections on document images."""

    def __init__(
        self, line_width: int = VIZ_LINE_WIDTH, font_size: int = VIZ_FONT_SIZE, alpha: float = VIZ_ALPHA
    ) -> None:
        """Initialize visualizer with display settings.

        Args:
            line_width: Width of bounding box lines
            font_size: Size of text labels
            alpha: Transparency for filled regions
        """
        self.line_width = line_width
        self.font_size = font_size
        self.alpha = alpha
        self.font = self._load_font()

    def _load_font(self) -> ImageFont.ImageFont:
        """Load a font for text labels."""
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]

        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, self.font_size)
            except (OSError, IOError):
                continue

        log.warning("Could not load TrueType font, using default")
        return ImageFont.load_default()

    def visualize_sections(
        self, image: Image.Image, sections: List[Dict], show_labels: bool = True, show_fill: bool = False
    ) -> Image.Image:
        """Draw section regions on image."""
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated, 'RGBA' if show_fill else 'RGB')
        log.info(f"Visualizing {len(sections)} layout sections")

        for idx, section in enumerate(sections):
            self._draw_section(draw, section, idx, show_labels, show_fill)

        return annotated

    def _draw_section(
        self, draw: ImageDraw.ImageDraw, section: Dict, idx: int, show_labels: bool, show_fill: bool
    ) -> None:
        """Draw a single section region."""
        rect = section.get('rect')
        if not rect or len(rect) != 4:
            log.warning(f"Skipping section {idx}: invalid rectangle {rect}")
            return

        x0, y0, x1, y1 = [float(v) for v in rect]
        section_type = section.get('section_type', 'default')
        color = SECTION_COLORS.get(section_type, SECTION_COLORS['default'])

        if show_fill:
            draw.rectangle([x0, y0, x1, y1], fill=color + (int(255 * self.alpha),), outline=None)

        draw.rectangle([x0, y0, x1, y1], outline=color, width=self.line_width)

        if show_labels:
            self._draw_label(draw, f"{idx}: {section_type}", x0, y0, color)

    def _draw_label(self, draw: ImageDraw.ImageDraw, label: str, x: float, y: float, color: tuple) -> None:
        """Draw a text label with background."""
        try:
            bbox = draw.textbbox((0, 0), label, font=self.font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except Exception:
            text_width = len(label) * self.font_size * 0.6
            text_height = self.font_size

        label_y = y - text_height - 2 if y > text_height + 4 else y + 2
        label_x = x + 2

        draw.rectangle(
            [label_x - 2, label_y - 2, label_x + text_width + 2, label_y + text_height + 2],
            fill=(255, 255, 255, 200),
        )
        draw.text((label_x, label_y), label, fill=color, font=self.font)

    def save_visualization(
        self,
        image: Image.Image,
        sections: List[Dict],
        output_path: str,
        show_labels: bool = True,
        show_fill: bool = False,
    ) -> None:
        """Create and save visualization to file."""
        annotated = self.visualize_sections(image, sections, show_labels, show_fill)
        annotated.save(output_path, "PNG")
        log.info(f"Saved visualization to {output_path}")
