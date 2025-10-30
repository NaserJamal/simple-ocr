# Level 02: Hybrid VLM OCR

## What You'll Learn

This level introduces an intelligent hybrid approach to PDF text extraction that combines:
- Fast PyMuPDF extraction for native text
- Vision Language Model (VLM) OCR for images
- Smart detection to minimize API costs

You'll learn how to build a production-ready OCR pipeline that handles real-world PDFs containing both text and images.

---

## The Problem with Pure Approaches

### PyMuPDF Only (Level 01)
- ❌ Cannot extract text from images
- ❌ Misses content in scanned pages
- ✅ Fast and free

### VLM Only
- ✅ Can read everything (text + images)
- ❌ Expensive (API costs per page)
- ❌ Slower (network latency)
- ❌ Overkill for native text

### Hybrid Solution (This Level)
- ✅ Uses PyMuPDF for native text (fast + free)
- ✅ Uses VLM only for pages with images
- ✅ **Best of both worlds**

---

## How It Works

```python
for i, page in enumerate(doc, 1):
    # Check if page has images
    images = page.get_images()
    has_images = len(images) > 0

    if has_images:
        # Page has images - send to VLM for OCR
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.pil_tobytes(format="PNG")
        img_b64 = base64.b64encode(img_bytes).decode()

        response = client.chat.completions.create(
            model=os.getenv("OCR_MODEL_NAME"),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all text from this image."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                ]
            }]
        )
        output.append(response.choices[0].message.content)
    else:
        # No images - use fast PyMuPDF extraction
        text = page.get_text().strip()
        output.append(text)
```

---

## Architecture Breakdown

### 1. Image Detection
```python
images = page.get_images()
has_images = len(images) > 0
```
PyMuPDF can detect if a page contains embedded images. This lets us decide which extraction method to use.

### 2. Page Rendering (for VLM)
```python
pix = page.get_pixmap(dpi=150)
img_bytes = pix.pil_tobytes(format="PNG")
img_b64 = base64.b64encode(img_bytes).decode()
```
- **`get_pixmap(dpi=150)`** - Renders the page as an image at 150 DPI
  - Higher DPI = better quality but larger files
  - 150 DPI is a good balance for text recognition
- **`pil_tobytes(format="PNG")`** - Converts to PNG bytes
- **Base64 encoding** - Required format for OpenAI API

### 3. VLM Request
```python
client.chat.completions.create(
    model=os.getenv("OCR_MODEL_NAME"),
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Extract all text from this image."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
        ]
    }]
)
```
Sends the page image to a vision model with a simple prompt: "Extract all text from this image."

**Supported models:**
- `gpt-4o` - Highest accuracy
- `gpt-4o-mini` - Good balance of cost/performance (recommended)
- `gpt-4-turbo` - Older but still capable
- Any OpenAI-compatible vision endpoint

---

## Prerequisites

- Python 3.8+
- OpenAI API key (or compatible endpoint)
- Internet connection (for VLM API calls)

---

## Setup

### Configure API credentials
Copy the `.env.example` from the root directory and fill in your credentials:

```bash
# From the project root
cp .env.example .env
```

Edit `.env`:
```env
OCR_MODEL_API_KEY=sk-your-actual-api-key-here
OCR_MODEL_BASE_URL=https://api.openai.com/v1
OCR_MODEL_NAME=gpt-4o-mini
```

**Where to get an API key:**
1. Sign up at [OpenAI Platform](https://platform.openai.com/)
2. Navigate to [API Keys](https://platform.openai.com/api-keys)
3. Create a new secret key
4. Copy it to your `.env` file

---

## Running the Example

```bash
# Make sure you're in the level directory
python main.py
```

**Expected output:**
```
Page 1: Found 2 image(s) - Sending to VLM
Page 2: No images - Using PyMuPDF text (1247 chars)
Page 3: Found 1 image(s) - Sending to VLM
```

The extracted text will be saved to `output/output.txt` in the current level directory.

---

## Cost Optimization Strategies

### 1. Smart Detection (Already Implemented)
Only send pages with images to the VLM. This can reduce costs by 50-90% for typical documents.

### 2. DPI Tuning
```python
pix = page.get_pixmap(dpi=150)  # Lower DPI = smaller images = lower cost
```
- 150 DPI: Good for most text
- 200 DPI: Better for small fonts
- 300 DPI: Best quality but 4x the cost

### 3. Model Selection
| Model | Cost (per 1M tokens) | Quality | Recommended |
|-------|----------------------|---------|-------------|
| gpt-4o-mini | $2.50 | Good | ✅ Start here |
| gpt-4o | $10.00 | Best | For critical docs |
| gpt-4-turbo | $20.00 | Great | Legacy option |

### 4. Batch Processing
For large document sets, consider:
- Rate limiting to avoid hitting API quotas
- Async processing for better throughput
- Caching results to avoid reprocessing

---

## Common Issues & Solutions

### Issue: "OpenAI API key not found"
**Solution:** Ensure your `.env` file exists at the project root and contains valid credentials.

### Issue: "Rate limit exceeded"
**Solution:** Add delays between requests or upgrade your OpenAI plan.

### Issue: "Low-quality OCR results"
**Solutions:**
- Increase DPI: `get_pixmap(dpi=200)` or `dpi=300`
- Try a better model: `gpt-4o` instead of `gpt-4o-mini`
- Improve the prompt: Add context about the document type

### Issue: "High costs"
**Solutions:**
- Verify image detection is working (check console output)
- Lower DPI if quality is acceptable
- Use `gpt-4o-mini` instead of `gpt-4o`

---

## Key Takeaways

1. **Hybrid approach** saves money while maintaining quality
2. **Image detection** is key to intelligent routing
3. **DPI affects** both quality and cost
4. **Model selection** impacts accuracy and budget
5. This pattern works for **any OpenAI-compatible vision API**

---

## Real-World Applications

This hybrid approach is ideal for:
- 📄 Invoice processing (mix of text and scanned signatures)
- 📊 Report digitization (charts, graphs, and text)
- 🏥 Medical records (forms with handwritten notes)
- 📋 Receipt scanning (photos + printed text)
- 📚 Document archives (mix of digital and scanned pages)

---

## Going Further

Consider these enhancements:
- **Parallel processing** - Process multiple pages concurrently
- **Structured extraction** - Use prompts to extract specific fields (dates, amounts, names)
- **Table detection** - Use VLMs to parse complex tables
- **Multi-language support** - VLMs handle 50+ languages out of the box
- **Confidence scoring** - Compare PyMuPDF vs VLM results for validation

---

## Related Resources

- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [OpenAI Vision API Guide](https://platform.openai.com/docs/guides/vision)
- [Best practices for OCR prompts](https://cookbook.openai.com/examples/vision_ocr)

---

## What's Next?

You've completed the core OCR fundamentals! Future levels could explore:
- Level 03: Structured data extraction (invoices, forms)
- Level 04: Multi-page document processing pipelines
- Level 05: Custom VLM fine-tuning for domain-specific OCR

👈 Back to [Level 01: Basic Text Extraction](../01-basic-text-extraction/README.md) | 👆 Back to [Main README](../../README.md)
