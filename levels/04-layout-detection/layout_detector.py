"""
Layout detection module using VLM
Handles communication with OpenAI-compatible API for layout analysis
"""

import json
import os
import logging
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv

from config import API_MAX_TOKENS, API_TEMPERATURE, PROMPT_FILE, TARGET_SIZE

log = logging.getLogger(__name__)

# Load environment variables
load_dotenv("../../.env")


class LayoutDetector:
    """Detects document layouts using Vision Language Model"""

    def __init__(self, prompt_file: str = PROMPT_FILE):
        """
        Initialize layout detector with API client

        Args:
            prompt_file: Path to the system prompt file
        """
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

    def detect_layouts(self, img_base64: str, page_num: int) -> List[Dict]:
        """
        Detect layout regions in a document image

        Args:
            img_base64: Base64-encoded PNG image
            page_num: Page number (for logging)

        Returns:
            List of layout dictionaries with keys:
                - layout_type: Type of layout region
                - rect: Bounding box [x0, y0, x1, y1] in image coordinates
                - confidence: Confidence level
                - description: Brief description
        """
        try:
            user_prompt = (
                f"Please analyze this document image (page {page_num + 1}) and detect all layout regions. "
                f"The image is {TARGET_SIZE}x{TARGET_SIZE} pixels (square canvas with document at top-left). "
                "Return rectangles in IMAGE PIXELS with origin at the top-left as [x0, y0, x1, y1]. "
                "Ensure x0 < x1 and y0 < y1 and keep values within the image bounds. "
                "Return ONLY the JSON array with no markdown formatting."
            )

            log.info(f"Sending page {page_num} to VLM for layout detection")

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

            # Parse the response
            layouts = self._parse_response(response_text, page_num)
            log.info(f"Detected {len(layouts)} layout regions on page {page_num}")

            return layouts

        except Exception as e:
            log.error(f"Failed to detect layouts for page {page_num}: {e}")
            return []

    def _parse_response(self, response_text: str, page_num: int) -> List[Dict]:
        """
        Parse VLM response into structured layout data

        Args:
            response_text: Raw response from VLM
            page_num: Page number (for logging)

        Returns:
            List of parsed layout dictionaries
        """
        try:
            cleaned = response_text.strip()

            # Remove markdown code fences if present
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line if it's ```
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            else:
                # Handle inline code blocks
                if "```" in cleaned:
                    parts = cleaned.split("```")
                    if len(parts) >= 3:
                        # Extract content between first pair of ```
                        inner = parts[1]
                        # Remove language identifier if present
                        if "\n" in inner:
                            cleaned = inner.split("\n", 1)[1].strip()
                        else:
                            cleaned = inner.strip()

            # Extract JSON array if embedded in text
            if not (cleaned.startswith("[") and cleaned.endswith("]")):
                start = cleaned.find("[")
                end = cleaned.rfind("]")
                if start != -1 and end != -1 and end > start:
                    cleaned = cleaned[start:end + 1]

            # Parse JSON
            layouts = json.loads(cleaned)

            if not isinstance(layouts, list):
                log.error(f"Response is not a list for page {page_num}")
                return []

            # Validate each layout
            valid_layouts = []
            for layout in layouts:
                if self._validate_layout(layout):
                    valid_layouts.append(layout)
                else:
                    log.warning(
                        f"Invalid layout on page {page_num}: "
                        f"{layout.get('layout_type', 'unknown')}"
                    )

            return valid_layouts

        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON for page {page_num}: {e}")
            log.debug(f"Response text: {response_text[:500]}")
            return []
        except Exception as e:
            log.error(f"Failed to parse response for page {page_num}: {e}")
            return []

    def _validate_layout(self, layout: Dict) -> bool:
        """
        Validate layout dictionary has required fields and valid values

        Args:
            layout: Layout dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required fields
            if not all(key in layout for key in ['layout_type', 'rect']):
                return False

            # Validate rect
            rect = layout['rect']
            if not isinstance(rect, list) or len(rect) != 4:
                return False

            x0, y0, x1, y1 = [float(v) for v in rect]

            # Check coordinate ordering
            if x0 >= x1 or y0 >= y1:
                return False

            # Check bounds (should be within TARGET_SIZE)
            if x0 < 0 or y0 < 0 or x1 > TARGET_SIZE or y1 > TARGET_SIZE:
                log.warning(
                    f"Layout rect out of bounds: [{x0}, {y0}, {x1}, {y1}], "
                    f"clamping to [{TARGET_SIZE}, {TARGET_SIZE}]"
                )
                # Clamp but don't reject
                layout['rect'] = [
                    max(0, min(TARGET_SIZE, x0)),
                    max(0, min(TARGET_SIZE, y0)),
                    max(0, min(TARGET_SIZE, x1)),
                    max(0, min(TARGET_SIZE, y1))
                ]

            return True

        except (TypeError, ValueError, KeyError) as e:
            log.warning(f"Layout validation error: {e}")
            return False
