"""Section detection module using VLM."""

import json
import logging
import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from src.infrastructure.config import API_MAX_TOKENS, API_TEMPERATURE, PROMPT_FILE, TARGET_SIZE

log = logging.getLogger(__name__)

load_dotenv("../../.env")


class SectionDetector:
    """Detects document layout sections using Vision Language Model."""

    def __init__(self, prompt_file: str = PROMPT_FILE, section_request: Optional[str] = None) -> None:
        """Initialize section detector with API client.

        Args:
            prompt_file: Path to system prompt file
            section_request: User's natural language description of specific section to find

        Raises:
            ValueError: If required environment variables are not set
            FileNotFoundError: If prompt file cannot be found
        """
        api_key = os.getenv("OCR_MODEL_API_KEY")
        base_url = os.getenv("OCR_MODEL_BASE_URL")
        self.model_name = os.getenv("OCR_MODEL_NAME")

        if not all([api_key, base_url, self.model_name]):
            raise ValueError(
                "OCR_MODEL_API_KEY, OCR_MODEL_BASE_URL, and OCR_MODEL_NAME must be set in .env"
            )

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.section_request = section_request
        self.system_prompt = self._load_prompt(prompt_file)

    def _load_prompt(self, prompt_file: str) -> str:
        """Load system prompt from file.

        Raises:
            FileNotFoundError: If prompt file cannot be found
        """
        prompt_path = os.path.join(os.path.dirname(__file__), prompt_file)
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    def detect_sections(self, img_base64: str, page_num: int) -> List[Dict]:
        """Detect layout sections in a document image."""
        try:
            user_prompt = self._build_user_prompt(page_num)

            log.info(
                f"Sending page {page_num} to VLM for section detection"
                + (f" (User request: '{self.section_request}')" if self.section_request else "")
            )

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=API_MAX_TOKENS,
                temperature=API_TEMPERATURE
            )

            response_text = response.choices[0].message.content or ""
            log.info(f"Received response for page {page_num}: {len(response_text)} chars")

            sections = self._parse_response(response_text, page_num)
            log.info(f"Detected {len(sections)} layout sections on page {page_num}")

            return sections

        except Exception as e:
            log.error(f"Failed to detect sections for page {page_num}: {e}")
            return []

    def _build_user_prompt(self, page_num: int) -> str:
        """Build user prompt based on section request."""
        base_instructions = (
            f"The image is {TARGET_SIZE}x{TARGET_SIZE} pixels (square canvas with document at top-left). "
            "Return rectangles in IMAGE PIXELS with origin at the top-left as [x0, y0, x1, y1]. "
            "Ensure x0 < x1 and y0 < y1 and keep values within the image bounds. "
            "Return ONLY the JSON array with no markdown formatting."
        )

        if self.section_request:
            return (
                f"Please analyze this document image (page {page_num + 1}). "
                f"The user wants to: '{self.section_request}'. "
                f"{base_instructions} "
                "Identify ONLY the specific section(s) that match the user's request."
            )
        else:
            return (
                f"Please analyze this document image (page {page_num + 1}) and identify the major layout sections. "
                f"{base_instructions} "
                "Focus on HIGH-LEVEL sections, not individual elements."
            )

    def _parse_response(self, response_text: str, page_num: int) -> List[Dict]:
        """Parse VLM response into structured section data"""
        try:
            cleaned = response_text.strip()

            # Remove markdown code fences
            if "```" in cleaned:
                start, end = cleaned.find("```"), cleaned.rfind("```")
                if start != -1 and end > start:
                    inner = cleaned[start + 3:end]
                    cleaned = inner.split("\n", 1)[1].strip() if "\n" in inner else inner.strip()

            # Extract JSON array
            if not cleaned.startswith("["):
                start, end = cleaned.find("["), cleaned.rfind("]")
                if start != -1 and end > start:
                    cleaned = cleaned[start:end + 1]

            sections = json.loads(cleaned)
            if not isinstance(sections, list):
                log.error(f"Response is not a list for page {page_num}")
                return []

            return [s for s in sections if self._validate_section(s, page_num)]

        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON for page {page_num}: {e}")
            log.debug(f"Response text: {response_text[:500]}")
            return []

    def _validate_section(self, section: Dict, page_num: int) -> bool:
        """Validate section dictionary has required fields and valid values"""
        try:
            if not all(k in section for k in ['section_type', 'rect']):
                return False

            rect = section['rect']
            if not isinstance(rect, list) or len(rect) != 4:
                return False

            x0, y0, x1, y1 = [float(v) for v in rect]
            if x0 >= x1 or y0 >= y1:
                return False

            # Clamp to bounds if needed
            if any(v < 0 or v > TARGET_SIZE for v in [x0, y0, x1, y1]):
                log.warning(f"Page {page_num}: Clamping out-of-bounds rect for {section['section_type']}")
                section['rect'] = [
                    max(0, min(TARGET_SIZE, x0)),
                    max(0, min(TARGET_SIZE, y0)),
                    max(0, min(TARGET_SIZE, x1)),
                    max(0, min(TARGET_SIZE, y1))
                ]
            return True

        except (TypeError, ValueError, KeyError) as e:
            log.warning(f"Section validation error: {e}")
            return False
