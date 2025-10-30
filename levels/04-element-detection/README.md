# Element Detection System

A robust, modular system for detecting document elements using Vision Language Models (VLMs). This system analyzes PDF pages and identifies different element regions (paragraphs, tables, headings, images, etc.) with precise bounding boxes.

## Architecture

The system follows a clean separation of concerns with the following structure:

```
levels/04-element-detection/
├── main.py                             # Clean entry point
└── utils/                              # Core modules
    ├── __init__.py                     # Package initialization
    ├── config.py                       # Configuration constants
    ├── image_processor.py              # PDF to image conversion
    ├── element_detector.py             # VLM-based element detection
    ├── visualizer.py                   # Visualization of detected elements
    ├── extractor.py                    # Main orchestration logic
    └── element_detection_prompt.txt    # System prompt for VLM
```

### Module Responsibilities

#### `main.py`
- Clean, concise entry point for the system
- Command-line argument handling
- Result formatting and display

#### `utils/config.py`
- Central configuration for all constants
- Color mappings for different element types
- API settings and file paths

#### `utils/image_processor.py`
- Converts PDF pages to properly sized images
- Implements resizing mechanism that improves VLM accuracy
- Handles coordinate denormalization back to original space
- Key features:
  - Renders at 1:1 scale (72 DPI) for pixel-to-point mapping
  - Resizes to fit target size while maintaining aspect ratio
  - Places on square canvas to prevent VLM preprocessing distortion

#### `utils/element_detector.py`
- Manages communication with OpenAI-compatible VLM API
- Sends images for element analysis
- Parses and validates VLM responses
- Handles JSON extraction from markdown-formatted responses

#### `utils/visualizer.py`
- Creates annotated images showing detected elements
- Draws bounding boxes with type-specific colors
- Adds labels for each element

#### `utils/extractor.py`
- Main orchestration logic
- Coordinates the complete pipeline:
  1. Load PDF
  2. Process each page
  3. Detect elements
  4. Create visualizations
  5. Save results
- Generates summary statistics

## Element Types Detected

The system can detect 14 different element types:

- **paragraph**: Regular text paragraphs and body content
- **heading**: Titles, section headers, and headings
- **table**: Tabular data and structured grids
- **list**: Bulleted or numbered lists
- **image**: Pictures, photos, diagrams, and illustrations
- **figure_caption**: Captions for images and figures
- **footer**: Page footers with page numbers, disclaimers
- **header**: Page headers with titles, logos
- **form_field**: Input fields, checkboxes, signature areas
- **signature**: Signature blocks and signature lines
- **date_field**: Date input areas
- **barcode**: Barcodes and QR codes
- **logo**: Company logos and branding elements
- **chart**: Charts, graphs, and data visualizations

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
python main.py
```

Specify a custom PDF:
```bash
python main.py /path/to/your/document.pdf
```

### Output

The system creates an `output/` directory containing:

1. **Visualizations**: `page_N_elements.png` for each page
   - Annotated images with colored bounding boxes
   - Labels showing element type and index

2. **JSON Results**: `elements.json`
   - Complete element data for all pages
   - Includes coordinates and element types

3. **Summary Statistics**: Printed to console
   - Total elements detected
   - Breakdown by element type
   - Success/failure counts

## Example Output

```
============================================================
ELEMENT DETECTION COMPLETE
============================================================
Pages processed: 3
Total elements detected: 47
Successful pages: 3
Failed pages: 0

Element types detected:
  - heading: 5
  - paragraph: 28
  - table: 8
  - image: 4
  - figure_caption: 2

Results saved to: output/
============================================================
```

## Design Decisions

### Why the Resizing Mechanism?

The image preprocessing approach was designed because:

1. **Prevents VLM preprocessing**: By providing a fixed-size square canvas, we avoid unpredictable resizing by the VLM
2. **Maintains aspect ratio**: Original document proportions are preserved
3. **Predictable coordinates**: Makes coordinate transformation more reliable
4. **Improved accuracy**: Reduces distortion that could affect element detection

### Coordinate System

- **Input**: VLM returns coordinates in padded image space (0-1001 pixels)
- **Processing**: Coordinates are denormalized back to original pixel space
- **Output**: Final coordinates match the original PDF page dimensions

This ensures that detected regions can be accurately used for:
- Cropping specific portions of the page
- Sending individual regions for detailed OCR
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
- Continues processing even if individual pages fail
- Logs detailed error information for debugging

## Integration Example

Using the system programmatically:

```python
from utils.extractor import ElementExtractor

# Create extractor
extractor = ElementExtractor("path/to/document.pdf", output_dir="results")

# Process document
result = extractor.process_document()

# Access results
for page_result in result['results']:
    page_num = page_result['page']
    elements = page_result['elements']

    for element in elements:
        element_type = element['layout_type']
        x0, y0, x1, y1 = element['rect']
        print(f"Page {page_num}: {element_type} at [{x0}, {y0}, {x1}, {y1}]")
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure all dependencies are installed
2. **API errors**: Check `.env` file configuration
3. **Out of memory**: Process fewer pages at a time for large PDFs
4. **Font loading errors**: Visualizer will fall back to default font

### Debug Mode

Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

## References

- Based on hybrid OCR approach from `levels/02-hybrid-vlm-ocr/`
- Uses PyMuPDF for PDF processing: https://pymupdf.readthedocs.io/
- Uses PIL/Pillow for image manipulation: https://pillow.readthedocs.io/

---

👈 Back to [Level 03: Smart Quality Detection](../03-smart-quality-detection/README.md) | 👉 Continue to [Level 05: Layout Detection](../05-layout-detection/README.md)
