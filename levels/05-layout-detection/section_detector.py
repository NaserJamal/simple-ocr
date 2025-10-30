"""
Section detection module using VLM
Handles communication with OpenAI-compatible API for layout section analysis
"""

import json
import os
import logging
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

from config import API_MAX_TOKENS, API_TEMPERATURE, PROMPT_FILE, TARGET_SIZE

log = logging.getLogger(__name__)

# Load environment variables
load_dotenv("../../.env")


class SectionDetector:
    """Detects document layout sections using Vision Language Model"""

    def __init__(self, prompt_file: str = PROMPT_FILE):
        """Initialize section detector with API client"""
        self.client = self._initialize_client()
        self.system_prompt = self._load_prompt(prompt_file)
        self.model_name = os.getenv("OCR_MODEL_NAME")

        if not self.model_name:
            raise ValueError("OCR_MODEL_NAME not found in environment variables")

    def _initialize_client(self) -> OpenAI:
        """Initialize OpenAI client with custom endpoint"""
        api_key = os.getenv("OCR_MODEL_API_KEY")
        base_url = os.getenv("OCR_MODEL_BASE_URL")

        if not api_key or not base_url:
            raise ValueError(
                "OCR_MODEL_API_KEY and OCR_MODEL_BASE_URL must be set in .env file"
            )

        return OpenAI(api_key=api_key, base_url=base_url)

    def _load_prompt(self, prompt_file: str) -> str:
        """Load system prompt from file"""
        try:
            prompt_path = os.path.join(os.path.dirname(__file__), prompt_file)
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            log.error(f"Prompt file not found: {prompt_file}")
            raise
        except Exception as e:
            log.error(f"Failed to load prompt file: {e}")
            raise

    def detect_sections(self, img_base64: str, page_num: int) -> List[Dict]:
        """Detect layout sections in a document image"""
        try:
            user_prompt = (
                f"Please analyze this document image (page {page_num + 1}) and identify the major layout sections. "
                f"The image is {TARGET_SIZE}x{TARGET_SIZE} pixels (square canvas with document at top-left). "
                "Focus on HIGH-LEVEL sections, not individual elements. "
                "Return rectangles in IMAGE PIXELS with origin at the top-left as [x0, y0, x1, y1]. "
                "Ensure x0 < x1 and y0 < y1 and keep values within the image bounds. "
                "Return ONLY the JSON array with no markdown formatting."
            )

            log.info(f"Sending page {page_num} to VLM for section detection")

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

    def _parse_response(self, response_text: str, page_num: int) -> List[Dict]:
        """Parse VLM response into structured section data"""
        try:
            cleaned = response_text.strip()

            # Remove markdown code fences
            if "```" in cleaned:
                start = cleaned.find("```")
                end = cleaned.rfind("```")
                if start != -1 and end != -1 and end > start:
                    inner = cleaned[start + 3:end]
                    # Remove language identifier if present
                    cleaned = inner.split("\n", 1)[1].strip() if "\n" in inner else inner.strip()

            # Extract JSON array
            if not cleaned.startswith("["):
                start = cleaned.find("[")
                end = cleaned.rfind("]")
                if start != -1 and end != -1 and end > start:
                    cleaned = cleaned[start:end + 1]

            sections = json.loads(cleaned)

            if not isinstance(sections, list):
                log.error(f"Response is not a list for page {page_num}")
                return []

            return [section for section in sections if self._validate_section(section, page_num)]

        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON for page {page_num}: {e}")
            log.debug(f"Response text: {response_text[:500]}")
            return []
        except Exception as e:
            log.error(f"Failed to parse response for page {page_num}: {e}")
            return []

    def _validate_section(self, section: Dict, page_num: int) -> bool:
        """Validate section dictionary has required fields and valid values"""
        try:
            if not all(key in section for key in ['section_type', 'rect']):
                return False

            rect = section['rect']
            if not isinstance(rect, list) or len(rect) != 4:
                return False

            x0, y0, x1, y1 = [float(v) for v in rect]

            if x0 >= x1 or y0 >= y1:
                return False

            # Clamp to bounds
            if x0 < 0 or y0 < 0 or x1 > TARGET_SIZE or y1 > TARGET_SIZE:
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
