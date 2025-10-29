# Simple OCR Tutorial

A practical, hands-on tutorial demonstrating PDF text extraction using PyMuPDF and Vision Language Models (VLMs).

---

## Overview

This repository teaches you how to extract text from PDFs through a progression of increasingly sophisticated approaches. Each level is self-contained with its own README, code, and dependencies.

**What makes this different?**
- ✅ Learn by doing with real, runnable examples
- ✅ Clear progression from simple to advanced
- ✅ Production-ready patterns and best practices
- ✅ Cost optimization strategies included

---

## What You'll Learn

By completing these levels, you'll understand:

1. **When to use PyMuPDF vs VLMs** - Different tools for different problems
2. **Cost optimization** - How to minimize API expenses with hybrid approaches
3. **Production patterns** - Real-world architectures for document processing
4. **Trade-offs** - Speed vs accuracy, cost vs quality

---

## Tutorial Levels

### [Level 01: Basic Text Extraction](levels/01-basic-text-extraction/)
**Learn:** PyMuPDF fundamentals for native PDF text extraction

- Fast, free, accurate extraction for digital PDFs
- Understanding native text vs image-based text
- When this approach works (and when it doesn't)

**Time:** 10 minutes
**Cost:** Free

---

### [Level 02: Hybrid VLM OCR](levels/02-hybrid-vlm-ocr/)
**Learn:** Intelligent routing between PyMuPDF and Vision Language Models

- Image detection to decide extraction method
- VLM integration for pages with images
- Cost optimization through smart routing
- Real-world production patterns

**Time:** 20 minutes
**Cost:** ~$0.01-0.10 per document (depends on image count)

---

## Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- OpenAI API key (for Level 02+)

### Getting Started

1. **Clone this repository**
```bash
git clone <repository-url>
cd simple-ocr
```

2. **Start with Level 01**
```bash
cd levels/01-basic-text-extraction
pip install -r requirements.txt
python extract.py
```

3. **Check the output**
```bash
cat ../../output/output.txt
```

4. **Read the level's README** to understand what happened

5. **Progress to the next level** when ready

---

## Project Structure

```
simple-ocr/
├── README.md                          # You are here
├── .env.example                       # API configuration template
├── PDF/                               # Sample PDF files
│   └── 1-page-text-img.pdf
├── output/                            # Extracted text output (gitignored)
└── levels/                            # Tutorial progression
    ├── 01-basic-text-extraction/      # PyMuPDF fundamentals
    │   ├── README.md
    │   ├── extract.py
    │   └── requirements.txt
    └── 02-hybrid-vlm-ocr/             # VLM integration
        ├── README.md
        ├── extract.py
        └── requirements.txt
```

---

## Configuration (Level 02+)

For levels that use Vision Language Models, you'll need API credentials:

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Add your API credentials to `.env`:
```env
OCR_MODEL_API_KEY=sk-your-api-key-here
OCR_MODEL_BASE_URL=https://api.openai.com/v1
OCR_MODEL_NAME=gpt-4o-mini
```

3. Get an API key from [OpenAI Platform](https://platform.openai.com/api-keys)

The `.env` file is gitignored and shared across all levels.

---

## Learning Path

**New to OCR?** Start with Level 01 to understand the basics.

**Have OCR experience?** Jump to Level 02 to see production patterns.

**Building a system?** Complete both levels, then see "Moving Forward" below.

---

## Key Concepts

### PyMuPDF
- Fast library for PDF manipulation
- Excellent for extracting native text
- Cannot read text from images

### Vision Language Models (VLMs)
- AI models that understand images
- Can perform OCR on scanned documents
- More expensive but handles complex cases

### Hybrid Approach
- Uses PyMuPDF for native text (fast + free)
- Uses VLM for pages with images (smart + accurate)
- Balances cost, speed, and accuracy

---

## Real-World Applications

These patterns are used for:
- 📄 Invoice processing
- 📊 Report digitization
- 🏥 Medical records extraction
- 📋 Receipt scanning
- 📚 Document archive digitization
- 🎓 Academic paper processing

---

## Moving Forward

### Building a Production System?

Once you've completed the tutorial levels, consider these enhancements:

**Infrastructure:**
- **Background Queue** - Redis/Celery for async processing at scale
- **Object Storage** - MinIO/S3 for reliable file persistence
- **Database** - PostgreSQL for metadata and search
- **Caching** - Redis for deduplication and results

**Features:**
- **Authentication** - Keycloak for user management
- **Monitoring** - Prometheus + Grafana for metrics
- **Rate Limiting** - Protect your API budget
- **Batch Processing** - Handle thousands of documents efficiently
- **Webhooks** - Notify when processing completes

**Quality:**
- **Confidence Scoring** - Validate extraction quality
- **Human Review** - Flag uncertain results
- **A/B Testing** - Compare different models/prompts
- **Error Recovery** - Retry failed pages gracefully

Each enhancement builds on the foundation you're learning in these tutorials.

---

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Make sure you're in the level directory and installed dependencies
cd levels/01-basic-text-extraction
pip install -r requirements.txt
```

**API errors (Level 02):**
- Verify `.env` exists at project root
- Check API key is valid
- Ensure you have API credits

**Output file not found:**
- The `output/` directory is created automatically
- Check `../../output/output.txt` relative to the level

---

## Contributing

Found a bug? Have an idea for a new level? Contributions are welcome!

---

## License

MIT License - Feel free to use these patterns in your own projects.

---

## Resources

- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [OpenAI Vision API Guide](https://platform.openai.com/docs/guides/vision)
- [PDF Structure Explained](https://pdfa.org/resource/pdf-specifications/)

---

**Ready to start?** 👉 Head to [Level 01: Basic Text Extraction](levels/01-basic-text-extraction/README.md)
