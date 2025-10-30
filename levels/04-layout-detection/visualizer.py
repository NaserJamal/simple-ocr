"""
Visualization module for layout detection results
Creates annotated images showing detected layout regions
"""

import logging
from typing import List, Dict
from PIL import Image, ImageDraw, ImageFont

from config import LAYOUT_COLORS, VIZ_LINE_WIDTH, VIZ_FONT_SIZE, VIZ_ALPHA

log = logging.getLogger(__name__)


class LayoutVisualizer:
    """Visualizes detected layout regions on document images"""

    def __init__(
        self,
        line_width: int = VIZ_LINE_WIDTH,
        font_size: int = VIZ_FONT_SIZE,
        alpha: float = VIZ_ALPHA
    ):
        """
        Initialize visualizer

        Args:
            line_width: Width of bounding box lines
            font_size: Font size for labels
            alpha: Transparency for filled regions (0.0 to 1.0)
        """
        self.line_width = line_width
        self.font_size = font_size
        self.alpha = alpha
        self.font = self._load_font()

    def _load_font(self) -> ImageFont.ImageFont:
        """Load a font for text labels"""
        try:
            # Try to load a system font
            return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", self.font_size)
        except Exception:
            try:
                # Fallback to another common font
                return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", self.font_size)
            except Exception:
                # Use default font as last resort
                log.warning("Could not load TrueType font, using default")
                return ImageFont.load_default()

    def visualize_layouts(
        self,
        image: Image.Image,
        layouts: List[Dict],
        show_labels: bool = True,
        show_fill: bool = False
    ) -> Image.Image:
        """
        Draw layout regions on image

        Args:
            image: PIL Image to annotate
            layouts: List of layout dictionaries with 'rect' and 'layout_type'
            show_labels: Whether to show text labels
            show_fill: Whether to fill regions with semi-transparent color

        Returns:
            Annotated PIL Image
        """
        # Create a copy to avoid modifying original
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated, 'RGBA' if show_fill else 'RGB')

        log.info(f"Visualizing {len(layouts)} layout regions")

        for idx, layout in enumerate(layouts):
            try:
                self._draw_layout(draw, layout, idx, show_labels, show_fill)
            except Exception as e:
                log.warning(f"Failed to draw layout {idx}: {e}")
                continue

        return annotated

    def _draw_layout(
        self,
        draw: ImageDraw.ImageDraw,
        layout: Dict,
        idx: int,
        show_labels: bool,
        show_fill: bool
    ):
        """Draw a single layout region"""
        rect = layout.get('rect')
        layout_type = layout.get('layout_type', 'default')

        if not rect or len(rect) != 4:
            log.warning(f"Invalid rect for layout {idx}")
            return

        x0, y0, x1, y1 = [float(v) for v in rect]

        # Get color for this layout type
        color = LAYOUT_COLORS.get(layout_type, LAYOUT_COLORS['default'])

        # Draw filled rectangle if requested
        if show_fill:
            fill_color = color + (int(255 * self.alpha),)  # Add alpha channel
            draw.rectangle([x0, y0, x1, y1], fill=fill_color, outline=None)

        # Draw bounding box
        draw.rectangle(
            [x0, y0, x1, y1],
            outline=color,
            width=self.line_width
        )

        # Draw label if requested
        if show_labels:
            label = self._create_label(layout, idx)
            self._draw_label(draw, label, x0, y0, color)

    def _create_label(self, layout: Dict, idx: int) -> str:
        """Create label text for a layout region"""
        layout_type = layout.get('layout_type', 'unknown')
        return f"{idx}: {layout_type}"

    def _draw_label(
        self,
        draw: ImageDraw.ImageDraw,
        label: str,
        x: float,
        y: float,
        color: tuple
    ):
        """Draw a text label with background"""
        # Calculate text size
        try:
            bbox = draw.textbbox((0, 0), label, font=self.font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except Exception:
            # Fallback for older Pillow versions
            text_width = len(label) * self.font_size * 0.6
            text_height = self.font_size

        # Position label above the box if possible, otherwise inside
        label_y = y - text_height - 2 if y > text_height + 4 else y + 2
        label_x = x + 2

        # Draw background rectangle for better readability
        background_padding = 2
        draw.rectangle(
            [
                label_x - background_padding,
                label_y - background_padding,
                label_x + text_width + background_padding,
                label_y + text_height + background_padding
            ],
            fill=(255, 255, 255, 200)  # Semi-transparent white
        )

        # Draw text
        draw.text((label_x, label_y), label, fill=color, font=self.font)

    def save_visualization(
        self,
        image: Image.Image,
        layouts: List[Dict],
        output_path: str,
        show_labels: bool = True,
        show_fill: bool = False
    ):
        """
        Create and save visualization to file

        Args:
            image: PIL Image to annotate
            layouts: List of layout dictionaries
            output_path: Path to save annotated image
            show_labels: Whether to show text labels
            show_fill: Whether to fill regions with semi-transparent color
        """
        try:
            annotated = self.visualize_layouts(image, layouts, show_labels, show_fill)
            annotated.save(output_path, "PNG")
            log.info(f"Saved visualization to {output_path}")
        except Exception as e:
            log.error(f"Failed to save visualization: {e}")
            raise

    def create_legend(self, width: int = 300, height: int = 400) -> Image.Image:
        """
        Create a legend image showing layout type colors

        Args:
            width: Width of legend image
            height: Height of legend image

        Returns:
            PIL Image with color legend
        """
        legend = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(legend)

        y_offset = 10
        box_size = 20
        padding = 5

        draw.text((10, y_offset), "Layout Types:", fill='black', font=self.font)
        y_offset += 25

        for layout_type, color in sorted(LAYOUT_COLORS.items()):
            if layout_type == 'default':
                continue

            # Draw color box
            draw.rectangle(
                [10, y_offset, 10 + box_size, y_offset + box_size],
                fill=color,
                outline='black'
            )

            # Draw type name
            draw.text(
                (10 + box_size + padding, y_offset + 2),
                layout_type.replace('_', ' ').title(),
                fill='black',
                font=self.font
            )

            y_offset += box_size + padding

        return legend
