# Simple OCR (for demonstration purposes)

Two approaches to extract text from PDFs:

## 1. Simple Extraction (`pymupdf_simple.py`)
Basic text extraction using PyMuPDF only.

```bash
python pymupdf_simple.py
```

## 2. VLM-Enhanced Extraction (`pymupdf_vlm.py`)
Smart extraction that uses PyMuPDF for text-only pages and sends pages with images to a Vision Language Model for OCR.

### Setup
1. Create a `.env`
2. Deploy a VLM on OICM
3. Fill in your OICM credentials:
   ```
   OCR_MODEL_API_KEY=your_api_key
   OCR_MODEL_BASE_URL=your_oicm_endpoint
   OCR_MODEL_NAME=your_model_name
   ```

### Run
```bash
python pymupdf_vlm.py
```

## Output
Both scripts save extracted text to `output.txt`.

## Requirements
```bash
pip install pymupdf openai python-dotenv
```

## Moving Forward

Want to build a production system? Consider adding:
- **Authentication** - Keycloak for user management and tracking
- **Deduplication** - Hash-based file detection to avoid reprocessing
- **Background Queue** - Redis for async processing at scale
- **Object Storage** - MinIO for reliable file persistence
- **Monitoring** - Prometheus + Grafana for metrics and alerts

Each enhancement builds on this simple foundation while maintaining the core OCR functionality.
