# Specific Location Text Extraction System

A robust, modular system for extracting text from specific sections of documents using Vision Language Models (VLMs). This system allows users to specify in natural language what section they want to extract (e.g., "extract the notes section"), or extract all major sections when no specific request is provided.

## Overview

This system provides flexible text extraction with two modes:

### Specific Section Mode (New!)
When you provide a natural language description of what you want:
1. Identifies **only the requested section** using VLM understanding
2. Crops that specific section as a separate image
3. Extracts text from the section using VLM OCR
4. Returns focused results for just what you asked for

**Example requests:**
- "extract the notes section"
- "find the summary"
- "get the comments"
- "extract the patient information"

### General Section Mode
When no specific request is provided:
1. Detects **all major layout sections** (e.g., header, experience, education, skills)
2. Crops each section as a separate image
3. Extracts text from sections **in parallel** using VLM OCR
4. Combines results into structured JSON and plain text files

This approach is ideal for documents like CVs, reports, forms, medical records, and any document where you need to extract specific information or understand the complete layout.

## Architecture

The system follows a clean separation of concerns with the following modules:

```
levels/07-specific-location/
├── main.py                        # Main entry point
├── utils/
│   ├── __init__.py
│   ├── config.py                  # Configuration constants
│   ├── image_processor.py         # PDF to image conversion with resizing
│   ├── section_detector.py        # VLM-based section detection
│   ├── text_extractor.py          # Parallel text extraction from sections
│   ├── visualizer.py              # Visualization of detected sections
│   ├── interactive_menu.py        # Interactive user interface
│   └── layout_detection_prompt.txt # System prompt for VLM
└── output/                        # Generated output files
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

#### `main.py`
- Main entry point for the system
- Orchestrates the complete pipeline:
  1. Load PDF
  2. Process each page
  3. Detect layout sections
  4. Extract text from sections in parallel
  5. Create visualizations
  6. Save results (JSON + TXT)
- Generates summary statistics

#### `interactive_menu.py`
- Provides interactive user interface
- Handles mode selection (new detection vs cached sections)
- Displays section selection menu
- Manages user prompts and input validation
- Shows extraction results and summaries

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

**Interactive Mode (Recommended):**
```bash
python main.py
```

The system will guide you through an interactive workflow:

**First Run (No cached sections):**
```
================================================================================
SPECIFIC LOCATION TEXT EXTRACTION
================================================================================

PDF: form-field-example.pdf

--------------------------------------------------------------------------------
What section would you like to extract?
Examples:
  - 'extract the notes section'
  - 'find the summary'
  - 'get the contact information'
  - Press Enter to detect and extract ALL sections
--------------------------------------------------------------------------------
Your request:
```

**Subsequent Runs (With cached sections):**
```
================================================================================
SPECIFIC LOCATION TEXT EXTRACTION
================================================================================

PDF: form-field-example.pdf

--------------------------------------------------------------------------------
Choose a mode:
  [1] Use existing sections (from previous detection)
  [2] Identify new sections (detect layout again)
--------------------------------------------------------------------------------
Your choice (1 or 2):
```

If you choose **[1] Use existing sections**, you'll see:
```
================================================================================
AVAILABLE SECTIONS
================================================================================

[1] Page 1 - Header Section
    Preview: Form Field Example...

[2] Page 1 - Content Block
    Preview: This is a sample form with various fields...

[3] Page 1 - Notes Section
    Preview: Additional notes and comments...

--------------------------------------------------------------------------------
Enter section numbers to extract (comma-separated, e.g., '1,3,5')
Or press Enter to extract all sections
--------------------------------------------------------------------------------
Your choice:
```

Then you can optionally provide context for extraction:
```
================================================================================
What do you want to extract from these sections?
Examples:
  - 'extract the notes'
  - 'find contact information'
  - Press Enter to extract all text as-is
--------------------------------------------------------------------------------
Your request:
```

This workflow allows you to:
- **Reuse detected sections** without re-running VLM detection (faster, cheaper)
- **Select specific sections** from previous detection
- **Provide new extraction context** for the same sections

**Command-Line Mode:**

Extract a specific section directly:
```bash
python main.py /path/to/document.pdf "extract the notes section"
```

**More examples with specific requests:**
```bash
# Extract summary section
python main.py document.pdf "find the summary"

# Extract contact information
python main.py document.pdf "get the contact information"

# Extract comments or notes
python main.py document.pdf "extract the comments"

# Extract patient details from medical form
python main.py medical_form.pdf "extract patient information"
```

**Specify a custom PDF (will prompt for section):**
```bash
python main.py /path/to/your/document.pdf
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

## How Specific Section Extraction Works

When you provide a natural language request like "extract the notes section", the system:

1. **Passes your request to the VLM** along with the document image
2. **VLM intelligently identifies** the section matching your description:
   - Uses semantic understanding (not just keyword matching)
   - Can map general terms to specific sections ("bio" → summary/contact info)
   - Can identify custom sections unique to your document ("notes", "findings", etc.)
3. **Returns only matching sections** with precise bounding boxes
4. **Extracts text with your context** - the VLM knows what you're looking for
5. **Saves results** focused on your specific request

This is more flexible than hardcoded section types because:
- Works with any document type
- Understands natural language variations
- Can identify domain-specific sections
- No need to know exact section names in advance

## Cached Sections Workflow

After the first run, sections are cached in `output/sections.json`. This enables:

### Benefits of Using Cached Sections:
1. **Faster Processing**: Skip VLM section detection (saves time and API costs)
2. **Consistent Boundaries**: Use the same section boundaries for different extractions
3. **Multiple Extractions**: Extract different information from the same sections
4. **Cost Effective**: Only pay for text extraction, not detection

### Example Use Cases:
- **First run**: Detect all sections with "Press Enter"
- **Second run**: Extract just section #3 (notes) with context "extract notes"
- **Third run**: Extract sections #1,2 with context "find contact info"

This workflow is ideal when you want to extract different information from the same document multiple times.

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
from main import LayoutTextExtractor

# Extract all sections
extractor = LayoutTextExtractor("path/to/document.pdf", output_dir="results", max_workers=5)
result = extractor.process_document()

# Extract a specific section
extractor = LayoutTextExtractor(
    "path/to/document.pdf",
    output_dir="results",
    section_request="extract the notes section"
)
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

Modify in `utils/config.py`:

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
