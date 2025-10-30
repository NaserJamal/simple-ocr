"""Text extraction module using VLM."""

import base64
import io
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

from src.infrastructure.config import OCR_MAX_TOKENS, OCR_TEMPERATURE

log = logging.getLogger(__name__)

load_dotenv("../../.env")


class TextExtractor:
    """Extracts text from document section images using VLM OCR."""

    def __init__(self, max_workers: int = 5, section_request: Optional[str] = None) -> None:
        """Initialize text extractor with API client.

        Args:
            max_workers: Number of parallel workers for extraction
            section_request: User's natural language description of what to extract

        Raises:
            ValueError: If required environment variables are not set
        """
        api_key = os.getenv("OCR_MODEL_API_KEY")
        base_url = os.getenv("OCR_MODEL_BASE_URL")
        self.model_name = os.getenv("OCR_MODEL_NAME")

        if not all([api_key, base_url, self.model_name]):
            raise ValueError(
                "OCR_MODEL_API_KEY, OCR_MODEL_BASE_URL, and OCR_MODEL_NAME must be set in .env"
            )

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.max_workers = max(1, max_workers)  # Ensure at least 1 worker
        self.section_request = section_request

    def extract_sections_parallel(
        self, page_image: Image.Image, sections: List[Dict], page_num: int
    ) -> List[Dict]:
        """Extract text from multiple sections in parallel."""
        if not sections:
            log.warning(f"No sections to extract on page {page_num}")
            return []

        log.info(f"Starting parallel text extraction for {len(sections)} sections on page {page_num}")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_section = {
                executor.submit(self._extract_section_text, page_image, section, page_num, idx): (
                    idx,
                    section,
                )
                for idx, section in enumerate(sections)
            }

            results = []
            for future in as_completed(future_to_section):
                idx, section = future_to_section[future]
                section_with_text = section.copy()
                section_with_text['index'] = idx

                try:
                    section_with_text['text'] = future.result()
                    log.info(
                        f"Page {page_num}, Section {idx}: "
                        f"Extracted {len(section_with_text['text'])} characters"
                    )
                except Exception as e:
                    log.error(f"Page {page_num}, Section {idx}: Extraction failed - {e}")
                    section_with_text['text'] = ""
                    section_with_text['error'] = str(e)

                results.append(section_with_text)

        results.sort(key=lambda x: x['index'])
        log.info(f"Completed parallel extraction for page {page_num}")
        return results

    def _extract_section_text(
        self, page_image: Image.Image, section: Dict, page_num: int, section_idx: int
    ) -> str:
        """Extract text from a single section."""
        try:
            x0, y0, x1, y1 = [int(v) for v in section['rect']]

            # Validate coordinates
            if x0 >= x1 or y0 >= y1:
                raise ValueError(f"Invalid coordinates: [{x0}, {y0}, {x1}, {y1}]")

            section_image = page_image.crop((x0, y0, x1, y1))
            img_base64 = self._image_to_base64(section_image)
            section_type = section.get('section_type', 'unknown')
            return self._ocr_image(img_base64, section_type, page_num, section_idx)
        except Exception as e:
            log.error(f"Failed to extract section {section_idx} on page {page_num}: {e}")
            raise

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def _ocr_image(self, img_base64: str, section_type: str, page_num: int, section_idx: int) -> str:
        """Perform OCR on a section image using VLM."""
        system_prompt = (
            "You are an expert OCR system. Extract ALL text from the image exactly as it appears. "
            "Preserve formatting, line breaks, and structure. "
            "Return ONLY the extracted text with no additional commentary or markdown formatting."
        )

        user_prompt = self._build_ocr_prompt(section_type)

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
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
            max_tokens=OCR_MAX_TOKENS,
            temperature=OCR_TEMPERATURE,
        )

        return (response.choices[0].message.content or "").strip()

    def _build_ocr_prompt(self, section_type: str) -> str:
        """Build OCR prompt based on section request."""
        section_type_formatted = section_type.replace('_', ' ')

        if self.section_request:
            return (
                f"The user requested: '{self.section_request}'\n\n"
                f"This is a {section_type_formatted} section that matches their request. "
                "Extract all text from this image exactly as it appears, maintaining the original structure and formatting. "
                "Focus on extracting the content the user is looking for."
            )
        else:
            return (
                f"Extract all text from this {section_type_formatted} section. "
                "Return the text exactly as it appears, maintaining the original structure and formatting."
            )
