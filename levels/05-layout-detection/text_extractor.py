"""
Text extraction module using VLM
Handles parallel text extraction from cropped section images
"""

import base64
import io
import os
import logging
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

from config import OCR_MAX_TOKENS, OCR_TEMPERATURE

log = logging.getLogger(__name__)

# Load environment variables
load_dotenv("../../.env")


class TextExtractor:
    """Extracts text from document section images using VLM OCR"""

    def __init__(self, max_workers: int = 5):
        """Initialize text extractor with API client"""
        api_key = os.getenv("OCR_MODEL_API_KEY")
        base_url = os.getenv("OCR_MODEL_BASE_URL")
        self.model_name = os.getenv("OCR_MODEL_NAME")

        if not all([api_key, base_url, self.model_name]):
            raise ValueError("OCR_MODEL_API_KEY, OCR_MODEL_BASE_URL, and OCR_MODEL_NAME must be set in .env")

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.max_workers = max_workers

    def extract_sections_parallel(self, page_image: Image.Image, sections: List[Dict], page_num: int) -> List[Dict]:
        """Extract text from multiple sections in parallel"""
        log.info(f"Starting parallel text extraction for {len(sections)} sections on page {page_num}")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_section = {
                executor.submit(self._extract_section_text, page_image, section, page_num, idx): (idx, section)
                for idx, section in enumerate(sections)
            }

            results = []
            for future in as_completed(future_to_section):
                idx, section = future_to_section[future]
                section_with_text = section.copy()
                section_with_text['index'] = idx

                try:
                    section_with_text['text'] = future.result()
                    log.info(f"Page {page_num}, Section {idx}: Extracted {len(section_with_text['text'])} characters")
                except Exception as e:
                    log.error(f"Page {page_num}, Section {idx}: Extraction failed - {e}")
                    section_with_text['text'] = ""
                    section_with_text['error'] = str(e)

                results.append(section_with_text)

        results.sort(key=lambda x: x['index'])
        log.info(f"Completed parallel extraction for page {page_num}")
        return results

    def _extract_section_text(self, page_image: Image.Image, section: Dict, page_num: int, section_idx: int) -> str:
        """Extract text from a single section"""
        x0, y0, x1, y1 = [int(v) for v in section['rect']]
        section_image = page_image.crop((x0, y0, x1, y1))
        img_base64 = self._image_to_base64(section_image)
        section_type = section.get('section_type', 'unknown')
        return self._ocr_image(img_base64, section_type, page_num, section_idx)

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def _ocr_image(self, img_base64: str, section_type: str, page_num: int, section_idx: int) -> str:
        """Perform OCR on a section image using VLM"""
        system_prompt = (
            "You are an expert OCR system. Extract ALL text from the image exactly as it appears. "
            "Preserve formatting, line breaks, and structure. "
            "Return ONLY the extracted text with no additional commentary or markdown formatting."
        )

        user_prompt = (
            f"Extract all text from this {section_type.replace('_', ' ')} section. "
            "Return the text exactly as it appears, maintaining the original structure and formatting."
        )

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_base64}", "detail": "high"}
                        }
                    ]
                }
            ],
            max_tokens=OCR_MAX_TOKENS,
            temperature=OCR_TEMPERATURE
        )

        return (response.choices[0].message.content or "").strip()
