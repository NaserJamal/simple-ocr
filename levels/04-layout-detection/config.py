"""
Configuration constants for layout detection system
"""

# Image preprocessing
TARGET_SIZE = 1001  # Target size for VLM processing (works well with Qwen)
RENDER_DPI = 72     # DPI for PDF rendering (1:1 pixel mapping)
RENDER_SCALE = 1    # Scale factor for PDF to image conversion

# Visualization
VIZ_LINE_WIDTH = 2  # Width of bounding box lines
VIZ_FONT_SIZE = 10  # Font size for labels
VIZ_ALPHA = 0.3     # Transparency for filled regions

# Color mapping for different layout types (RGB)
LAYOUT_COLORS = {
    'paragraph': (0, 0, 255),        # Blue
    'heading': (255, 0, 0),          # Red
    'table': (0, 255, 0),            # Green
    'list': (255, 165, 0),           # Orange
    'image': (128, 0, 128),          # Purple
    'figure_caption': (255, 192, 203), # Pink
    'footer': (128, 128, 128),       # Gray
    'header': (64, 64, 64),          # Dark Gray
    'form_field': (255, 255, 0),     # Yellow
    'signature': (255, 0, 255),      # Magenta
    'date_field': (0, 255, 255),     # Cyan
    'barcode': (165, 42, 42),        # Brown
    'logo': (255, 215, 0),           # Gold
    'chart': (0, 128, 128),          # Teal
    'default': (128, 128, 128)       # Gray fallback
}

# API settings
API_MAX_TOKENS = 16000
API_TEMPERATURE = 0.1

# File paths
OUTPUT_DIR = "output"
PROMPT_FILE = "layout_detection_prompt.txt"
