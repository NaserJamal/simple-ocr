"""
Configuration constants for element detection system
"""

# Image preprocessing
TARGET_SIZE = 1001  # Target size for VLM processing (works well with Qwen)
RENDER_DPI = 72     # DPI for PDF rendering (1:1 pixel mapping)
RENDER_SCALE = 1    # Scale factor for PDF to image conversion

# Visualization
VIZ_LINE_WIDTH = 2  # Width of bounding box lines
VIZ_FONT_SIZE = 10  # Font size for labels
VIZ_ALPHA = 0.3     # Transparency for filled regions

# Color mapping for different element types (RGB)
ELEMENT_COLORS = {
    'paragraph': (0, 0, 200),        # Blue
    'heading': (200, 0, 0),          # Red
    'table': (0, 150, 0),            # Dark Green
    'list': (200, 100, 0),           # Dark Orange
    'image': (128, 0, 128),          # Purple
    'figure_caption': (200, 0, 100), # Dark Pink
    'footer': (80, 80, 80),          # Dark Gray
    'header': (50, 50, 50),          # Very Dark Gray
    'form_field': (180, 180, 0),     # Dark Yellow
    'signature': (180, 0, 180),      # Dark Magenta
    'date_field': (0, 150, 150),     # Dark Cyan
    'barcode': (139, 35, 35),        # Dark Brown
    'logo': (200, 150, 0),           # Dark Gold
    'chart': (0, 100, 100),          # Dark Teal
    'default': (80, 80, 80)          # Dark Gray fallback
}

# API settings
API_MAX_TOKENS = 16000
API_TEMPERATURE = 0.1

# File paths
OUTPUT_DIR = "output"
PROMPT_FILE = "element_detection_prompt.txt"
