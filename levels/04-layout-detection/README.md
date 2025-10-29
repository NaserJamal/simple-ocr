# Layout Detection System

A robust, modular system for detecting document layouts using Vision Language Models (VLMs). This system analyzes PDF pages and identifies different layout regions (paragraphs, tables, headings, images, etc.) with precise bounding boxes.

## Architecture

The system follows a clean separation of concerns with the following modules:

```
levels/04-layout-detection/
├── config.py                      # Configuration constants
├── image_processor.py             # PDF to image conversion with resizing
├── layout_detector.py             # VLM-based layout detection
├── visualizer.py                  # Visualization of detected layouts
├── extract_layouts.py             # Main orchestration script
└── layout_detection_prompt.txt    # System prompt for VLM
```

### Module Responsibilities

#### `config.py`
- Central configuration for all constants
- Color mappings for different layout types
- API settings and file paths

#### `image_processor.py`
- Converts PDF pages to properly sized images
- Implements resizing mechanism that improves VLM accuracy
- Handles coordinate denormalization back to original space
- Key features:
  - Renders at 1:1 scale (72 DPI) for pixel-to-point mapping
  - Resizes to fit target size while maintaining aspect ratio
  - Places on square canvas to prevent VLM preprocessing distortion

#### `layout_detector.py`
- Manages communication with OpenAI-compatible VLM API
- Sends images for layout analysis
- Parses and validates VLM responses
- Handles JSON extraction from markdown-formatted responses

#### `visualizer.py`
- Creates annotated images showing detected layouts
- Draws bounding boxes with type-specific colors
- Adds labels with confidence levels
- Generates color legend for layout types

#### `extract_layouts.py`
- Main entry point for the system
- Orchestrates the complete pipeline:
  1. Load PDF
  2. Process each page
  3. Detect layouts
  4. Create visualizations
  5. Save results
- Generates summary statistics

## Layout Types Detected

The system can detect 14 different layout types:

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
python extract_layouts.py
```

Specify a custom PDF:
```bash
python extract_layouts.py /path/to/your/document.pdf
```

### Output

The system creates an `output/` directory containing:

1. **Visualizations**: `page_N_layout.png` for each page
   - Annotated images with colored bounding boxes
   - Labels showing layout type and confidence

2. **JSON Results**: `layouts.json`
   - Complete layout data for all pages
   - Includes coordinates, types, confidence, and descriptions

3. **Summary Statistics**: Printed to console
   - Total layouts detected
   - Breakdown by layout type
   - Success/failure counts

## Example Output

```
============================================================
LAYOUT DETECTION COMPLETE
============================================================
Pages processed: 3
Total layouts detected: 47
Successful pages: 3
Failed pages: 0

Layout types detected:
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

The image preprocessing approach (from `form_fields.py`) was preserved because:

1. **Prevents VLM preprocessing**: By providing a fixed-size square canvas, we avoid unpredictable resizing by the VLM
2. **Maintains aspect ratio**: Original document proportions are preserved
3. **Predictable coordinates**: Makes coordinate transformation more reliable
4. **Improved accuracy**: Reduces distortion that could affect layout detection

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

## Future Enhancements

Potential improvements for this system:

1. **Region Extraction**: Add functionality to crop and save individual layout regions
2. **Batch Processing**: Process multiple PDFs in parallel
3. **Custom Prompts**: Allow runtime prompt customization
4. **Confidence Filtering**: Filter out low-confidence detections
5. **Region OCR**: Automatically run OCR on text regions
6. **Interactive Viewer**: Web-based UI for viewing results

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

## Integration Example

Using the system programmatically:

```python
from extract_layouts import LayoutExtractor

# Create extractor
extractor = LayoutExtractor("path/to/document.pdf", output_dir="results")

# Process document
result = extractor.process_document()

# Access results
for page_result in result['results']:
    page_num = page_result['page']
    layouts = page_result['layouts']

    for layout in layouts:
        layout_type = layout['layout_type']
        x0, y0, x1, y1 = layout['rect']
        confidence = layout['confidence']
        print(f"Page {page_num}: {layout_type} at [{x0}, {y0}, {x1}, {y1}] ({confidence})")
```

## References

- Based on hybrid OCR approach from `levels/02-hybrid-vlm-ocr/`
- Inspired by field detection system in original `form_fields.py`
- Uses PyMuPDF for PDF processing: https://pymupdf.readthedocs.io/
- Uses PIL/Pillow for image manipulation: https://pillow.readthedocs.io/
