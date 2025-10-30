"""
Configuration constants for layout detection and text extraction system
"""

# Image preprocessing
TARGET_SIZE = 1001  # Target size for VLM processing (works well with Qwen)
RENDER_DPI = 72     # DPI for PDF rendering (1:1 pixel mapping)
RENDER_SCALE = 1    # Scale factor for PDF to image conversion

# Visualization
VIZ_LINE_WIDTH = 3  # Width of bounding box lines
VIZ_FONT_SIZE = 12  # Font size for labels
VIZ_ALPHA = 0.2     # Transparency for filled regions

# Color mapping for different section types (RGB)
SECTION_COLORS = {
    'header_section': (200, 0, 0),       # Red
    'title_block': (150, 0, 0),          # Dark Red
    'contact_info': (0, 150, 200),       # Cyan
    'summary_section': (100, 0, 200),    # Purple
    'experience_section': (0, 150, 0),   # Green
    'education_section': (0, 100, 200),  # Blue
    'skills_section': (200, 100, 0),     # Orange
    'projects_section': (200, 150, 0),   # Gold
    'references_section': (100, 100, 100), # Gray
    'content_block': (0, 0, 150),        # Dark Blue
    'table_section': (0, 150, 100),      # Teal
    'sidebar': (150, 0, 150),            # Magenta
    'footer_section': (80, 80, 80),      # Dark Gray
    'multi_column_section': (150, 100, 50), # Brown
    'default': (80, 80, 80)              # Dark Gray fallback
}

# API settings for section detection
API_MAX_TOKENS = 16000
API_TEMPERATURE = 0.1

# API settings for text extraction
OCR_MAX_TOKENS = 8000
OCR_TEMPERATURE = 0.0

# File paths
OUTPUT_DIR = "output"
PROMPT_FILE = "layout_detection_prompt.txt"
