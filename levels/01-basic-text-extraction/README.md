# Level 01: Basic Text Extraction with PyMuPDF

## What You'll Learn

This level introduces the fundamentals of PDF text extraction using PyMuPDF. You'll learn how to:
- Open and read PDF documents programmatically
- Extract embedded text from PDF pages
- Understand when native text extraction works (and when it doesn't)

---

## Concept: Native Text Extraction

PDFs store text in two ways:

1. **Native text** - Characters stored as selectable text (you can highlight and copy them)
2. **Image-based text** - Text rendered as part of images (scanned documents, screenshots)

PyMuPDF excels at extracting **native text** directly from the PDF structure. This is:
- ⚡ Fast (no AI or image processing needed)
- ✅ Accurate (preserves exact characters)
- 💰 Free (no API costs)

**Limitation**: PyMuPDF cannot read text from images. For that, you'll need OCR (covered in Level 02).

---

## How It Works

```python
import pymupdf

# Open the PDF document
doc = pymupdf.open("../../PDF/1-page-text-img.pdf")

# Extract text from each page and join with newlines
text = "\n".join(page.get_text() for page in doc)

# Save to output file
open("output/output.txt", "w").write(text)
```

**Step-by-step breakdown:**

1. **`pymupdf.open(path)`** - Opens the PDF and returns a document object
2. **`for page in doc`** - Iterates through each page in the document
3. **`page.get_text()`** - Extracts all native text from that page
4. **`"\n".join(...)`** - Combines all pages with newlines between them
5. **Save result** - Writes extracted text to `output/output.txt`

---

## Prerequisites

- Python 3.8+
- pip (Python package manager)

---

## Installation

```bash
# Navigate to this level's directory
cd levels/01-basic-text-extraction

# Install dependencies
pip install -r requirements.txt
```

---

## Running the Example

```bash
# Make sure you're in the level directory
python extract.py
```

**Expected output:**
```
# No console output - check output/output.txt for results
```

The extracted text will be saved to `output/output.txt` in the current level directory.

---

## When to Use This Approach

✅ **Use native PyMuPDF extraction when:**
- PDFs contain selectable text (digital documents, reports, invoices)
- Speed and cost are priorities
- You need 100% accurate character preservation

❌ **Don't use this approach when:**
- PDFs contain scanned images or screenshots
- Text is embedded in graphics/charts
- You need to extract text from photos within the PDF

For those cases, proceed to **Level 02: Hybrid VLM OCR** →

---

## Key Takeaways

1. PyMuPDF provides fast, accurate extraction for native PDF text
2. The `get_text()` method handles most standard PDFs with ease
3. This approach has zero cost and minimal dependencies
4. It cannot handle image-based text (that's where VLMs come in)

---

## What's Next?

Most real-world PDFs contain **both** native text and images with text. Level 02 introduces a hybrid approach that:
- Uses PyMuPDF for fast text extraction
- Detects pages with images
- Sends images to a Vision Language Model (VLM) for OCR

👉 Continue to [Level 02: Hybrid VLM OCR](../02-hybrid-vlm-ocr/README.md)
