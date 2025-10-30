"""
Element Detection System - Utilities Package

Contains core modules for PDF element detection:
- config: Configuration constants
- image_processor: PDF to image conversion
- element_detector: VLM-based element detection
- visualizer: Element visualization
- extractor: Main orchestration logic
"""

from .config import (
    TARGET_SIZE,
    RENDER_SCALE,
    OUTPUT_DIR,
    ELEMENT_COLORS
)
from .image_processor import ImageProcessor
from .element_detector import ElementDetector
from .visualizer import ElementVisualizer
from .extractor import ElementExtractor

__all__ = [
    'TARGET_SIZE',
    'RENDER_SCALE',
    'OUTPUT_DIR',
    'ELEMENT_COLORS',
    'ImageProcessor',
    'ElementDetector',
    'ElementVisualizer',
    'ElementExtractor',
]
