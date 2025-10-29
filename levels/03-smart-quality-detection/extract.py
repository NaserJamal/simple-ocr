import pymupdf
import os
import base64
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv("../../.env")

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OCR_MODEL_API_KEY"),
    base_url=os.getenv("OCR_MODEL_BASE_URL")
)


def assess_text_quality(text: str) -> dict:
    """
    Assess the quality of extracted text using multiple heuristics.
    Returns a dict with quality score (0-100) and reasons for low quality.
    """
    if not text or len(text.strip()) == 0:
        return {"score": 0, "reasons": ["No text extracted"]}

    reasons = []
    penalties = []

    # Normalize text for analysis
    cleaned = text.strip()

    # 1. Check ratio of alphanumeric characters
    alphanum = sum(c.isalnum() or c.isspace() for c in cleaned)
    alphanum_ratio = alphanum / len(cleaned) if cleaned else 0
    if alphanum_ratio < 0.7:
        penalty = (0.7 - alphanum_ratio) * 50
        penalties.append(penalty)
        reasons.append(f"Low alphanumeric ratio ({alphanum_ratio:.2%})")

    # 2. Check for excessive special characters (common in poor OCR)
    special_chars = len(re.findall(r'[^\w\s.,!?;:()\-\'"@#$%&]', cleaned))
    special_ratio = special_chars / len(cleaned) if cleaned else 0
    if special_ratio > 0.1:
        penalty = (special_ratio - 0.1) * 100
        penalties.append(penalty)
        reasons.append(f"Excessive special characters ({special_ratio:.2%})")

    # 3. Check for words (space-separated tokens with reasonable length)
    words = cleaned.split()
    valid_words = [w for w in words if 1 <= len(w) <= 50 and any(c.isalpha() for c in w)]
    word_ratio = len(valid_words) / len(words) if words else 0
    if word_ratio < 0.5 and len(words) > 5:
        penalty = (0.5 - word_ratio) * 60
        penalties.append(penalty)
        reasons.append(f"Low valid word ratio ({word_ratio:.2%})")

    # 4. Check average word length (too short or too long indicates issues)
    if valid_words:
        avg_word_len = sum(len(w) for w in valid_words) / len(valid_words)
        if avg_word_len < 2 or avg_word_len > 15:
            penalty = 20
            penalties.append(penalty)
            reasons.append(f"Unusual average word length ({avg_word_len:.1f})")

    # 5. Check for repeated characters (common OCR artifact)
    repeated_chars = len(re.findall(r'(.)\1{4,}', cleaned))
    if repeated_chars > 0:
        penalty = min(repeated_chars * 10, 30)
        penalties.append(penalty)
        reasons.append(f"Repeated character sequences detected ({repeated_chars})")

    # 6. Check for minimum text length (very short text might be incomplete)
    if len(cleaned) < 20:
        penalty = 15
        penalties.append(penalty)
        reasons.append(f"Very short text ({len(cleaned)} chars)")

    # Calculate final score
    total_penalty = sum(penalties)
    score = max(0, 100 - total_penalty)

    return {
        "score": score,
        "reasons": reasons if score < 70 else []
    }


def extract_with_vlm(page, page_num: int) -> str:
    """Extract text from page using VLM."""
    print(f"  → Sending page {page_num} to VLM for extraction")

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


# Quality threshold (0-100)
QUALITY_THRESHOLD = 70

doc = pymupdf.open("../../PDF/1-page-text-img.pdf")
output = []

for i, page in enumerate(doc, 1):
    print(f"\nPage {i}:")

    # Extract text with PyMuPDF
    text = page.get_text().strip()

    # Assess quality
    quality = assess_text_quality(text)
    print(f"  PyMuPDF extraction quality: {quality['score']:.1f}/100")

    if quality['reasons']:
        print(f"  Issues detected: {', '.join(quality['reasons'])}")

    # Decide: use PyMuPDF if quality is good, otherwise VLM
    if quality['score'] >= QUALITY_THRESHOLD:
        print(f"  ✓ Using PyMuPDF text ({len(text)} chars)")
        output.append(text)
    else:
        print(f"  ✗ Quality below threshold ({QUALITY_THRESHOLD}) - Using VLM")
        vlm_text = extract_with_vlm(page, i)
        output.append(vlm_text)

# Write results
open("output/output.txt", "w").write("\n".join(output))
print(f"\n✓ Extraction complete - saved to output/output.txt")
