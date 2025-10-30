# Level 03: Smart Quality Detection

## What You'll Learn

This level introduces intelligent quality assessment for PDF text extraction:
- Automated quality scoring of PyMuPDF extractions
- Multi-heuristic text analysis
- Smart VLM fallback for poor-quality extractions
- Production-ready confidence thresholds

You'll learn how to build a self-correcting OCR pipeline that automatically detects when text extraction fails and switches to a more robust method.

---

## The Evolution of OCR Intelligence

### Level 01: PyMuPDF Only
- ✅ Fast and free
- ❌ No validation of extraction quality
- ❌ Silent failures on poor extractions

### Level 02: Hybrid Image Detection
- ✅ Uses VLM for pages with images
- ✅ Fast PyMuPDF for text-only pages
- ❌ Assumes PyMuPDF always extracts text correctly
- ❌ No quality validation

### Level 03: Smart Quality Detection (This Level)
- ✅ Validates PyMuPDF extraction quality
- ✅ Uses VLM as fallback for poor extractions
- ✅ Multi-heuristic quality scoring
- ✅ **Self-correcting pipeline**

---

## How It Works

```python
# Extract text with PyMuPDF
text = page.get_text().strip()

# Assess extraction quality
quality = assess_text_quality(text)

# Use VLM if quality is poor
if quality['score'] >= QUALITY_THRESHOLD:
    output.append(text)  # Use PyMuPDF
else:
    vlm_text = extract_with_vlm(page, i)  # Fallback to VLM
    output.append(vlm_text)
```

---

## Quality Assessment Algorithm

The `assess_text_quality()` function evaluates extracted text using 6 heuristics:

### 1. Alphanumeric Ratio
```python
alphanum_ratio = alphanum / len(cleaned)
# Expected: > 70% for clean text
```
Detects garbled or corrupted text with excessive noise.

### 2. Special Character Ratio
```python
special_ratio = special_chars / len(cleaned)
# Expected: < 10% for clean text
```
Identifies OCR artifacts and encoding issues (e.g., `####`, `@@@`, `^^^`).

### 3. Valid Word Ratio
```python
word_ratio = len(valid_words) / len(words)
# Expected: > 50% for meaningful text
```
Checks if space-separated tokens form reasonable words.

### 4. Average Word Length
```python
avg_word_len = sum(len(w) for w in valid_words) / len(valid_words)
# Expected: 2-15 characters
```
Unusual word lengths indicate extraction issues.

### 5. Repeated Character Sequences
```python
repeated_chars = len(re.findall(r'(.)\1{4,}', cleaned))
# Expected: 0 occurrences
```
Detects common OCR artifacts like `aaaaa` or `-----`.

### 6. Minimum Text Length
```python
if len(cleaned) < 20:
    # Penalty applied
```
Very short extractions may indicate incomplete processing.

---

## Quality Score Examples

### ✅ High Quality (Score: 100)
```
"This is a well-formed sentence with proper words and structure."
```
**Result:** Use PyMuPDF extraction

### ❌ Low Quality (Score: 46)
```
"###@@@ !!!! ^^^^ **** %%%% &&&& $$$$ ####"
```
**Issues:** Low alphanumeric ratio (36%), excessive special characters (17%), no valid words
**Result:** Fallback to VLM

### ⚠️ Edge Case (Score: 0)
```
""
```
**Issues:** No text extracted
**Result:** Fallback to VLM

---

## Architecture Breakdown

### 1. Quality Assessment
```python
def assess_text_quality(text: str) -> dict:
    """Returns score (0-100) and reasons for low quality."""

    # Calculate penalties for each heuristic
    penalties = []
    reasons = []

    # Apply 6 quality checks...

    score = max(0, 100 - sum(penalties))
    return {"score": score, "reasons": reasons}
```

### 2. Smart Decision Making
```python
QUALITY_THRESHOLD = 70  # Configurable threshold

if quality['score'] >= QUALITY_THRESHOLD:
    # High quality - use PyMuPDF
    output.append(text)
else:
    # Low quality - use VLM
    vlm_text = extract_with_vlm(page, i)
    output.append(vlm_text)
```

### 3. VLM Fallback
```python
def extract_with_vlm(page, page_num: int) -> str:
    """Extract text from page using VLM."""
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
    return response.choices[0].message.content
```

---

## Prerequisites

- Python 3.8+
- OpenAI API key (or compatible endpoint)
- Internet connection (for VLM fallback)

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
Page 1:
  PyMuPDF extraction quality: 100.0/100
  ✓ Using PyMuPDF text (595 chars)

✓ Extraction complete - saved to output/output.txt
```

**Example with poor quality:**
```
Page 1:
  PyMuPDF extraction quality: 45.2/100
  Issues detected: Low alphanumeric ratio (38.45%), Excessive special characters (15.23%)
  ✗ Quality below threshold (70) - Using VLM
  → Sending page 1 to VLM for extraction

✓ Extraction complete - saved to output/output.txt
```

---

## Tuning the Quality Threshold

### Default Threshold: 70/100
```python
QUALITY_THRESHOLD = 70  # Balance of quality and cost
```

### Aggressive Mode: 85/100
```python
QUALITY_THRESHOLD = 85  # Prioritize quality over cost
```
- More pages sent to VLM
- Higher accuracy
- Increased API costs

### Conservative Mode: 50/100
```python
QUALITY_THRESHOLD = 50  # Prioritize cost over quality
```
- Fewer VLM calls
- Lower costs
- May accept mediocre extractions

### Recommendation
- **Start with 70** - Good balance for most use cases
- **Use 85** for critical documents (legal, medical)
- **Use 50** for low-stakes bulk processing

---

## Real-World Scenarios

### Scenario 1: Clean Digital PDF
```
PyMuPDF extraction: "The quick brown fox jumps over the lazy dog."
Quality score: 100/100
Decision: ✓ Use PyMuPDF (free, instant)
```

### Scenario 2: Poor Scan Quality
```
PyMuPDF extraction: "Th3 qu!ck br0wn f0x jum##s 0v3r th3 l@zy d0g"
Quality score: 52/100
Decision: ✗ Use VLM ($0.002, 2 seconds)
```

### Scenario 3: Corrupted Encoding
```
PyMuPDF extraction: "������������������"
Quality score: 0/100
Decision: ✗ Use VLM (rescue operation)
```

### Scenario 4: Empty Page
```
PyMuPDF extraction: ""
Quality score: 0/100
Decision: ✗ Use VLM (might detect faint text)
```

---

## Cost-Benefit Analysis

### Typical 100-page Document
| Extraction Type | Pages | Cost | Time |
|----------------|-------|------|------|
| Pure PyMuPDF | 100 | $0 | 5s |
| Pure VLM | 100 | $0.20 | 200s |
| Smart Quality (Level 03) | 90 PyMuPDF + 10 VLM | $0.02 | 25s |

**Savings:** 90% cost reduction vs pure VLM
**Quality:** Catches extraction failures automatically

---

## Common Issues & Solutions

### Issue: Too many VLM fallbacks
**Symptoms:** Most pages trigger VLM despite looking correct

**Solutions:**
1. Lower the threshold: `QUALITY_THRESHOLD = 60`
2. Check PDF encoding: Some fonts trigger false positives
3. Review specific heuristics: Adjust penalties in `assess_text_quality()`

### Issue: Missing extraction failures
**Symptoms:** Poor extractions not caught by quality check

**Solutions:**
1. Raise the threshold: `QUALITY_THRESHOLD = 80`
2. Add domain-specific heuristics (e.g., check for expected keywords)
3. Enable manual review for scores near threshold

### Issue: "OpenAI API key not found"
**Solution:** Ensure your `.env` file exists at the project root with valid credentials.

### Issue: "Rate limit exceeded"
**Solution:** Add delays between VLM requests or upgrade your OpenAI plan.

---

## Advanced Customization

### Custom Heuristics
Add domain-specific quality checks:

```python
def assess_text_quality(text: str) -> dict:
    # ... existing checks ...

    # Custom: Check for expected document structure
    if "Invoice" in text or "Total:" in text:
        # Invoice should have numbers
        if not re.search(r'\d+\.\d{2}', text):
            penalties.append(20)
            reasons.append("Missing expected currency format")

    return {"score": score, "reasons": reasons}
```

### Logging Quality Metrics
Track quality over time:

```python
import json

quality_log = []
for i, page in enumerate(doc, 1):
    text = page.get_text().strip()
    quality = assess_text_quality(text)

    quality_log.append({
        "page": i,
        "score": quality['score'],
        "method": "pymupdf" if quality['score'] >= 70 else "vlm",
        "reasons": quality['reasons']
    })

with open("quality_report.json", "w") as f:
    json.dump(quality_log, f, indent=2)
```

---

## Key Takeaways

1. **Quality validation** prevents silent extraction failures
2. **Multi-heuristic scoring** catches diverse error patterns
3. **Configurable thresholds** balance quality and cost
4. **VLM fallback** provides automatic self-correction
5. **This pattern works** for any PDF extraction pipeline

---

## Real-World Applications

This smart quality detection is ideal for:
- 📄 **Legal documents** - Cannot afford extraction errors
- 🏥 **Medical records** - Quality is critical for patient safety
- 💰 **Financial statements** - Accuracy required for compliance
- 📊 **Data pipelines** - Automatic quality assurance
- 🔍 **Archive digitization** - Mixed quality source documents

---

## Performance Comparison

### Level 01 (PyMuPDF Only)
- Speed: ⭐⭐⭐⭐⭐
- Cost: ⭐⭐⭐⭐⭐
- Reliability: ⭐⭐ (no validation)

### Level 02 (Hybrid Image Detection)
- Speed: ⭐⭐⭐⭐
- Cost: ⭐⭐⭐⭐
- Reliability: ⭐⭐⭐ (assumes PyMuPDF works)

### Level 03 (Smart Quality Detection)
- Speed: ⭐⭐⭐⭐
- Cost: ⭐⭐⭐⭐
- Reliability: ⭐⭐⭐⭐⭐ (self-correcting)

---

## Going Further

Consider these enhancements:
- **Machine learning** - Train a classifier to predict extraction quality
- **Language detection** - Adjust thresholds for different languages
- **Confidence scoring** - Use VLM to score its own extractions
- **Human-in-the-loop** - Flag borderline cases (60-80) for review
- **A/B comparison** - Run both methods and compare results

---

## Related Resources

- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [OpenAI Vision API Guide](https://platform.openai.com/docs/guides/vision)
- [Text Quality Metrics in NLP](https://aclanthology.org/)

---

## What's Next?

You've built a production-ready, self-correcting OCR pipeline! Future levels could explore:
- Level 04: Structured data extraction (invoices, forms)
- Level 05: Multi-language document processing
- Level 06: Table detection and parsing

👈 Back to [Level 02: Hybrid VLM OCR](../02-hybrid-vlm-ocr/README.md) | 👆 Back to [Main README](../../README.md)
