# Level 06: Template-Based Document Parsing

## What You'll Learn

This level introduces a template-based approach to structured data extraction from documents using Vision Language Models (VLMs). You'll learn how to:
- Create document-specific extraction templates
- Use VLMs for structured JSON extraction
- Build a modular, extensible parsing system
- Handle multiple document types with different schemas

---

## Overview

Instead of generic OCR, this level focuses on **structured data extraction** from specific document types (e.g., ID cards, invoices, forms). Each template defines:
- The expected data schema (JSON format)
- Extraction instructions for the VLM
- Field validation rules

---

## Architecture

```
levels/06-template-based-parsing/
├── extract.py              # Main parser script
├── templates/              # Document type templates
│   └── uae_emirates_id.txt # UAE Emirates ID template
├── output/                 # Extracted JSON files
└── README.md
```

### Key Components

1. **Template System** (`TEMPLATES` dict in extract.py:11)
   - Defines available document types
   - Maps template keys to prompt files
   - Easily extensible for new document types

2. **Template Prompts** (`templates/*.txt`)
   - Instructs VLM on what to extract
   - Defines the expected JSON schema
   - Provides extraction guidelines

3. **Interactive Selection** (`select_template()` in extract.py:30)
   - User chooses document type
   - Supports selection by number or key
   - Validates user input

4. **VLM Extraction** (`extract_with_vlm()` in extract.py:66)
   - Sends image + template prompt to VLM
   - Uses `temperature=0` for deterministic output
   - Returns structured JSON

---

## How It Works

### Flow

```
1. User runs script
   ↓
2. Selects document template (e.g., "eid")
   ↓
3. Provides image path
   ↓
4. System loads template prompt
   ↓
5. Converts image to base64
   ↓
6. Sends to VLM with extraction instructions
   ↓
7. VLM returns structured JSON
   ↓
8. Saves to output/extracted_<template>.json
```

### Example UAE Emirates ID Template

```json
{
  "id_number": "784-1234-1234567-1",
  "full_name": "JOHN DOE",
  "full_name_arabic": "جون دو",
  "nationality": "United Arab Emirates",
  "date_of_birth": "01/01/1990",
  "gender": "Male",
  "issue_date": "01/01/2020",
  "expiry_date": "01/01/2030",
  "card_number": null
}
```

---

## Installation & Setup

### 1. Install dependencies
```bash
cd levels/06-template-based-parsing
pip install -r requirements.txt
```

### 2. Configure API credentials
Ensure your `.env` file exists at the project root with:

```env
OCR_MODEL_API_KEY=sk-your-actual-api-key-here
OCR_MODEL_BASE_URL=https://api.openai.com/v1
OCR_MODEL_NAME=gpt-4o-mini
```

---

## Running the Parser

```bash
python extract.py
```

### Interactive Flow

```
========================================
Template-Based Document Parser
========================================

Available Templates:
----------------------------------------
1. [eid] UAE Emirates ID
----------------------------------------

Select a template (enter number or key): 1

Selected: UAE Emirates ID

Enter the path to the image/document: /path/to/emirates_id.jpg

Processing image with template: UAE Emirates ID...

Extracted data saved to: output/extracted_eid.json

Extracted Data:
{
  "id_number": "784-1234-1234567-1",
  "full_name": "JOHN DOE",
  ...
}
```

---

## Adding New Templates

### Step 1: Create Template Prompt

Create a new file in `templates/` (e.g., `templates/passport.txt`):

```
You are an expert at extracting structured information from passports.

Extract ALL available information from this passport image and return it in the following JSON format:

{
  "passport_number": "string",
  "full_name": "string",
  "nationality": "string",
  "date_of_birth": "string (DD/MM/YYYY format)",
  "issue_date": "string (DD/MM/YYYY format)",
  "expiry_date": "string (DD/MM/YYYY format)"
}

IMPORTANT:
- Use null for fields not visible
- Return ONLY valid JSON
- Preserve exact spelling from document
```

### Step 2: Register Template

Add to `TEMPLATES` dict in `extract.py`:

```python
TEMPLATES = {
    "eid": {
        "name": "UAE Emirates ID",
        "prompt_file": "templates/uae_emirates_id.txt"
    },
    "passport": {
        "name": "International Passport",
        "prompt_file": "templates/passport.txt"
    }
}
```

That's it! The template is now available for selection.

---

## Best Practices

### Template Design

1. **Be Specific**: Clearly define expected field names and formats
2. **Use Examples**: Show the exact JSON structure expected
3. **Handle Missing Data**: Specify how to handle missing fields (use `null`)
4. **Validate Format**: Request specific date formats, case conventions, etc.
5. **Error Handling**: Include instructions for invalid documents

### Extraction Tips

1. **Use `temperature=0`**: Ensures consistent, deterministic output
2. **Image Quality**: Higher resolution = better accuracy (but higher cost)
3. **Clear Instructions**: Be explicit about what to extract and how
4. **JSON Only**: Request pure JSON output to simplify parsing

---

## Code Highlights

### Modular Functions

```python
# Clean separation of concerns
load_template_prompt()  # Template loading
select_template()       # User interaction
image_to_base64()       # Image processing
extract_with_vlm()      # VLM extraction
save_output()           # Result saving
```

### Error Handling

- File existence validation (extract.py:133)
- Template validation (extract.py:22)
- JSON parsing with fallback (extract.py:104-116)
- Graceful error messages (extract.py:145-147)

### Extensibility

- Add templates without modifying core logic
- Template prompts are separate text files
- Easy to version control templates
- Simple TEMPLATES dict configuration

---

## Common Issues & Solutions

### Issue: "Template not found"
**Solution**: Ensure template key exists in `TEMPLATES` dict and prompt file exists in `templates/` directory.

### Issue: "Not valid JSON" warning
**Solution**:
- Improve template prompt clarity
- Add "Return ONLY valid JSON, no explanation" to prompt
- Use `temperature=0` for consistency

### Issue: Incorrect field values
**Solutions**:
- Increase image quality/resolution
- Make template prompt more specific
- Add examples to the prompt
- Use a more capable model (e.g., `gpt-4o`)

---

## Key Takeaways

1. **Templates** enable structured extraction from specific document types
2. **Modular design** makes adding new templates trivial
3. **VLMs** can extract complex structured data with proper prompting
4. **JSON output** simplifies downstream processing
5. **Interactive selection** provides user-friendly experience

---

## Real-World Applications

This template-based approach is ideal for:
- **Identity Verification**: Passports, ID cards, driver's licenses
- **Financial Processing**: Invoices, receipts, bank statements
- **Forms Processing**: Applications, surveys, contracts
- **Medical Records**: Prescriptions, lab results, insurance cards
- **Business Documents**: Purchase orders, shipping labels, certificates

---

## Performance & Costs

### Model Recommendations

| Document Type | Recommended Model | Why |
|---------------|------------------|-----|
| Simple IDs | gpt-4o-mini | Cost-effective, sufficient accuracy |
| Complex forms | gpt-4o | Better field recognition |
| Handwritten docs | gpt-4o | Superior OCR capabilities |

### Cost Optimization

- Use smallest model that meets accuracy requirements
- Batch similar documents together
- Cache results to avoid reprocessing
- Optimize image size (balance quality vs. cost)

---

## Going Further

Consider these enhancements:
- **Batch processing**: Process multiple documents at once
- **Validation layer**: Verify extracted data against expected patterns
- **Confidence scores**: Add field-level confidence metrics
- **Multi-page support**: Handle documents spanning multiple pages
- **Database integration**: Save results to a database
- **API endpoint**: Expose as a web service

---

## Related Resources

- [OpenAI Vision API Guide](https://platform.openai.com/docs/guides/vision)
- [Structured Output Best Practices](https://cookbook.openai.com/examples/structured_outputs)
- [JSON Schema Validation](https://json-schema.org/)

---

## What's Next?

You've built a production-ready template-based extraction system! Consider exploring:
- Multi-template processing (extract different document types in batch)
- Fine-tuning models on your specific document types
- Building a web UI for easier document upload
- Integrating with document management systems

---

👆 Back to [Main README](../../README.md)
