# Layout-Based Text Extraction System

A robust, modular system for extracting text from documents using Vision Language Models (VLMs). This system analyzes PDF pages, identifies major layout sections, and extracts text from each section in parallel for efficient processing.

## Overview

Unlike traditional OCR that processes entire pages or individual elements, this system:
1. Detects **major layout sections** (e.g., header, experience, education, skills)
2. Crops each section as a separate image
3. Extracts text from sections **in parallel** using VLM OCR
4. Combines results into structured JSON and plain text files

This approach is ideal for documents like CVs, reports, and forms where content is organized into distinct sections.

## Architecture

The system follows a clean separation of concerns with the following modules:

```
levels/05-layout-detection/
├── config.py                      # Configuration constants
├── image_processor.py             # PDF to image conversion with resizing
├── section_detector.py            # VLM-based section detection
├── text_extractor.py              # Parallel text extraction from sections
├── visualizer.py                  # Visualization of detected sections
├── extract_text.py                # Main orchestration script
└── layout_detection_prompt.txt    # System prompt for VLM
```

### Module Responsibilities

#### `config.py`
- Central configuration for all constants
- Color mappings for different section types
- API settings for detection and OCR
- File paths and visualization settings

#### `image_processor.py`
- Converts PDF pages to properly sized images
- Implements resizing mechanism that improves VLM accuracy
- Handles coordinate denormalization back to original space
- Key features:
  - Renders at 1:1 scale (72 DPI) for pixel-to-point mapping
  - Resizes to fit target size while maintaining aspect ratio
  - Places on square canvas to prevent VLM preprocessing distortion

#### `section_detector.py`
- Manages communication with OpenAI-compatible VLM API
- Sends images for layout section analysis
- Parses and validates VLM responses
- Handles JSON extraction from markdown-formatted responses
- Focuses on **high-level sections**, not individual elements

#### `text_extractor.py`
- Extracts text from cropped section images using VLM OCR
- Implements **parallel extraction** using ThreadPoolExecutor
- Configurable number of concurrent workers
- Robust error handling for individual sections

#### `visualizer.py`
- Creates annotated images showing detected sections
- Draws bounding boxes with type-specific colors
- Adds labels for each section

#### `extract_text.py`
- Main entry point for the system
- Orchestrates the complete pipeline:
  1. Load PDF
  2. Process each page
  3. Detect layout sections
  4. Extract text from sections in parallel
  5. Create visualizations
  6. Save results (JSON + TXT)
- Generates summary statistics

## Section Types Detected

The system can detect 14 different section types optimized for documents:

- **header_section**: Top section with page headers, titles, logos, contact info
- **title_block**: Main title or heading area at the top of the document
- **contact_info**: Contact details section (address, phone, email, etc.)
- **summary_section**: Executive summary, profile, or overview sections
- **experience_section**: Work experience, employment history sections
- **education_section**: Education, qualifications, certifications sections
- **skills_section**: Skills, competencies, expertise sections
- **projects_section**: Projects, portfolio, achievements sections
- **references_section**: References or recommendations section
- **content_block**: General content area (paragraphs, text blocks)
- **table_section**: Large table or structured data section
- **sidebar**: Side column with supplementary information
- **footer_section**: Bottom section with footers, disclaimers, page numbers
- **multi_column_section**: Section with multiple columns of text

## Usage

### Prerequisites

1. Install required dependencies:
```bash
pip install pymupdf pillow openai python-dotenv
```

2. Set up environment variables in `../../.env`:
```env
OCR_MODEL_API_KEY=your_api_key
OCR_MODEL_BASE_URL=your_base_url
OCR_MODEL_NAME=your_model_name
```

### Running the System

Basic usage (uses default PDF):
```bash
python extract_text.py
```

Specify a custom PDF:
```bash
python extract_text.py /path/to/your/document.pdf
```

### Output

The system creates an `output/` directory containing:

1. **Visualizations**: `page_N_sections.png` for each page
   - Annotated images with colored bounding boxes
   - Labels showing section type and index

2. **JSON Results**: `sections.json`
   - Complete section data for all pages
   - Includes coordinates, section types, and extracted text
   - Structured format for programmatic access

3. **Text Results**: `extracted_text.txt`
   - Plain text file with all extracted content
   - Organized by page and section type
   - Easy to read and process

4. **Summary Statistics**: Printed to console
   - Total sections detected
   - Breakdown by section type
   - Character count
   - Success/failure counts

## Example Output

```
================================================================================
LAYOUT-BASED TEXT EXTRACTION COMPLETE
================================================================================
Pages processed: 2
Total sections detected: 8
Total characters extracted: 3542
Successful pages: 2
Failed pages: 0

Section types detected:
  - contact_info: 1
  - education_section: 1
  - experience_section: 1
  - header_section: 1
  - skills_section: 2
  - summary_section: 2

Results saved to: output/
  - sections.json: Detailed section data with extracted text
  - extracted_text.txt: Combined extracted text
  - page_N_sections.png: Visualizations
================================================================================
```

## Design Decisions

### Why Layout Sections Instead of Elements?

This system focuses on **high-level sections** rather than individual elements because:

1. **Parallel Processing**: Large sections can be processed in parallel, making better use of resources
2. **Context Preservation**: Keeping related content together improves OCR accuracy
3. **Practical Output**: Users typically want text organized by logical sections, not individual elements
4. **Efficiency**: Fewer VLM calls (3-10 per page vs 50+ for elements)

### Why Parallel Text Extraction?

The parallel extraction approach provides:

1. **Speed**: Multiple sections processed simultaneously using ThreadPoolExecutor
2. **Scalability**: Configurable worker count to match available resources
3. **Resilience**: Individual section failures don't stop the entire process
4. **Efficiency**: Better utilization of VLM API throughput

### Coordinate System

- **Input**: VLM returns coordinates in padded image space (0-1001 pixels)
- **Processing**: Coordinates are denormalized back to original pixel space
- **Output**: Final coordinates match the original PDF page dimensions

This ensures that detected regions can be accurately used for:
- Cropping specific sections of the page
- Sending individual sections for detailed OCR
- Further processing or analysis

### Modular Design

The system is intentionally broken into focused modules:

- **Easy to understand**: Each module has a single, clear responsibility
- **Easy to test**: Modules can be tested independently
- **Easy to extend**: New features can be added to specific modules
- **Easy to maintain**: Bug fixes are isolated to relevant modules

### Robust Error Handling

- Validates VLM responses before processing
- Gracefully handles parsing errors
- Continues processing even if individual sections fail
- Logs detailed error information for debugging
- Collects partial results when some sections succeed

## Integration Example

Using the system programmatically:

```python
from extract_text import LayoutTextExtractor

# Create extractor
extractor = LayoutTextExtractor("path/to/document.pdf", output_dir="results", max_workers=5)

# Process document
result = extractor.process_document()

# Access results
for page_result in result['results']:
    page_num = page_result['page']
    sections = page_result['sections']

    for section in sections:
        section_type = section['section_type']
        text = section['text']
        x0, y0, x1, y1 = section['rect']
        print(f"Page {page_num} - {section_type}:")
        print(f"  Location: [{x0}, {y0}, {x1}, {y1}]")
        print(f"  Text: {text[:100]}...")
```

## Performance Tuning

### Adjust Parallel Workers

Control the number of concurrent text extraction tasks:

```python
# More workers = faster but more memory/API usage
extractor = LayoutTextExtractor("doc.pdf", max_workers=10)

# Fewer workers = slower but more conservative
extractor = LayoutTextExtractor("doc.pdf", max_workers=3)
```

### API Settings

Modify in `config.py`:

```python
# Section detection settings
API_MAX_TOKENS = 16000
API_TEMPERATURE = 0.1

# Text extraction settings
OCR_MAX_TOKENS = 8000
OCR_TEMPERATURE = 0.0
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure all dependencies are installed
2. **API errors**: Check `.env` file configuration
3. **Out of memory**: Reduce `max_workers` parameter
4. **Font loading errors**: Visualizer will fall back to default font
5. **Too many small sections**: VLM may be detecting elements instead of sections
   - Solution: Refine the system prompt to emphasize larger sections

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Comparison with Element Detection

| Aspect | Layout Detection (This) | Element Detection |
|--------|------------------------|-------------------|
| Granularity | High-level sections (3-10 per page) | Individual elements (50+ per page) |
| Use Case | Text extraction, document parsing | Layout analysis, precise element location |
| Speed | Faster (fewer VLM calls) | Slower (many VLM calls) |
| Text Quality | Better (more context) | Variable (less context) |
| Output | Structured text by section | Bounding boxes and types |

## References

- Based on element detection approach from earlier version
- Uses PyMuPDF for PDF processing: https://pymupdf.readthedocs.io/
- Uses PIL/Pillow for image manipulation: https://pillow.readthedocs.io/
- Uses ThreadPoolExecutor for parallel processing: https://docs.python.org/3/library/concurrent.futures.html

---

👈 Back to [Level 04: Element Detection](../04-element-detection/README.md) | 👉 Continue to [Level 06: Template-Based Parsing](../06-template-based-parsing/README.md)
