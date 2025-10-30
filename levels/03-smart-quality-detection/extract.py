import pymupdf
import os
import base64
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv("../../.env")

client = OpenAI(
    api_key=os.getenv("OCR_MODEL_API_KEY"),
    base_url=os.getenv("OCR_MODEL_BASE_URL")
)


def assess_text_quality(text: str) -> dict:
    """
    Assess the quality of extracted text using multiple heuristics.
    Returns a dict with quality score (0-100) and reasons for low quality.
    """
    if not text or not text.strip():
        return {"score": 0, "reasons": ["No text extracted"]}

    cleaned = text.strip()
    text_len = len(cleaned)
    reasons = []
    penalty = 0

    # 1. Alphanumeric ratio
    alphanum_ratio = sum(c.isalnum() or c.isspace() for c in cleaned) / text_len
    if alphanum_ratio < 0.7:
        penalty += (0.7 - alphanum_ratio) * 50
        reasons.append(f"Low alphanumeric ratio ({alphanum_ratio:.2%})")

    # 2. Special characters
    special_ratio = len(re.findall(r'[^\w\s.,!?;:()\-\'"@#$%&]', cleaned)) / text_len
    if special_ratio > 0.1:
        penalty += (special_ratio - 0.1) * 100
        reasons.append(f"Excessive special characters ({special_ratio:.2%})")

    # 3. Valid words ratio
    words = cleaned.split()
    if words:
        valid_words = [w for w in words if 1 <= len(w) <= 50 and any(c.isalpha() for c in w)]
        word_ratio = len(valid_words) / len(words)
        if word_ratio < 0.5 and len(words) > 5:
            penalty += (0.5 - word_ratio) * 60
            reasons.append(f"Low valid word ratio ({word_ratio:.2%})")

        # 4. Average word length
        if valid_words:
            avg_word_len = sum(len(w) for w in valid_words) / len(valid_words)
            if avg_word_len < 2 or avg_word_len > 15:
                penalty += 20
                reasons.append(f"Unusual average word length ({avg_word_len:.1f})")

    # 5. Repeated characters
    repeated_chars = len(re.findall(r'(.)\1{4,}', cleaned))
    if repeated_chars > 0:
        penalty += min(repeated_chars * 10, 30)
        reasons.append(f"Repeated character sequences detected ({repeated_chars})")

    # 6. Minimum text length
    if text_len < 20:
        penalty += 15
        reasons.append(f"Very short text ({text_len} chars)")

    score = max(0, 100 - penalty)
    return {"score": score, "reasons": reasons if score < 70 else []}


def extract_with_vlm(page, page_num: int) -> str:
    """Extract text from page using VLM."""
    print(f"  → Sending page {page_num} to VLM for extraction")

    pix = page.get_pixmap(dpi=150)
    img_b64 = base64.b64encode(pix.pil_tobytes(format="PNG")).decode()

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


QUALITY_THRESHOLD = 70

doc = pymupdf.open("../../PDF/1-page-text-img.pdf")
output = []

for i, page in enumerate(doc, 1):
    print(f"\nPage {i}:")

    text = page.get_text().strip()
    quality = assess_text_quality(text)

    print(f"  PyMuPDF extraction quality: {quality['score']:.1f}/100")
    if quality['reasons']:
        print(f"  Issues detected: {', '.join(quality['reasons'])}")

    if quality['score'] >= QUALITY_THRESHOLD:
        print(f"  ✓ Using PyMuPDF text ({len(text)} chars)")
        output.append(text)
    else:
        print(f"  ✗ Quality below threshold ({QUALITY_THRESHOLD}) - Using VLM")
        output.append(extract_with_vlm(page, i))

with open("output/output.txt", "w") as f:
    f.write("\n".join(output))

print(f"\n✓ Extraction complete - saved to output/output.txt")
