"""
Configuration constants for template-based document parsing
"""

# Image preprocessing
TARGET_SIZE = 1001  # Target size for VLM processing (works well with vision models)
RENDER_SCALE = 1    # Scale factor for PDF to image conversion

# API settings for extraction
API_TEMPERATURE = 0.0  # Deterministic output for structured extraction
