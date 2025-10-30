"""
Markdown reconstruction module
Takes extracted markdown sections and reconstructs them into a cohesive document
"""

import os
import logging
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

from .config import RECONSTRUCTION_MAX_TOKENS, RECONSTRUCTION_TEMPERATURE

log = logging.getLogger(__name__)

# Load environment variables
load_dotenv("../../.env")


class MarkdownReconstructor:
    """Reconstructs extracted markdown sections into a cohesive document"""

    def __init__(self):
        """Initialize reconstructor with API client"""
        api_key = os.getenv("OCR_MODEL_API_KEY")
        base_url = os.getenv("OCR_MODEL_BASE_URL")
        self.model_name = os.getenv("OCR_MODEL_NAME")

        if not all([api_key, base_url, self.model_name]):
            raise ValueError("OCR_MODEL_API_KEY, OCR_MODEL_BASE_URL, and OCR_MODEL_NAME must be set in .env")

        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def reconstruct_document(self, all_results: List[Dict]) -> str:
        """
        Reconstruct a complete markdown document from extracted sections

        Args:
            all_results: List of page results, each containing sections with extracted text

        Returns:
            Reconstructed markdown document as a string
        """
        log.info("Reconstructing markdown document from extracted sections")

        # Gather all extracted text with context
        sections_text = self._gather_sections_text(all_results)

        if not sections_text.strip():
            log.warning("No text extracted from document")
            return "# Empty Document\n\nNo text could be extracted from this document."

        # Send to VLM for reconstruction
        reconstructed = self._reconstruct_with_vlm(sections_text)

        log.info(f"Reconstruction complete: {len(reconstructed)} characters")
        return reconstructed

    def _gather_sections_text(self, all_results: List[Dict]) -> str:
        """Gather all extracted text from all pages and sections"""
        gathered_parts = []

        for page_result in all_results:
            page_num = page_result.get('page', 0)
            sections = page_result.get('sections', [])

            if not sections:
                continue

            gathered_parts.append(f"\n--- PAGE {page_num + 1} ---\n")

            for section in sections:
                section_type = section.get('section_type', 'unknown')
                text = section.get('text', '')

                if text.strip():
                    gathered_parts.append(f"\n[Section Type: {section_type}]\n{text}\n")

        return '\n'.join(gathered_parts)

    def _reconstruct_with_vlm(self, sections_text: str) -> str:
        """Use VLM to reconstruct cohesive markdown from sections"""
        system_prompt = (
            "You are an expert document reconstruction assistant. "
            "You will receive text extracted from different sections of a document, "
            "with each section labeled by its type (e.g., header, title, content, etc.).\n\n"
            "Your task is to reconstruct these sections into a single, cohesive, well-formatted markdown document. "
            "Follow these guidelines:\n\n"
            "1. Organize content logically based on document structure\n"
            "2. Use appropriate markdown headings (# ## ###) to create hierarchy\n"
            "3. Preserve all important information from the sections\n"
            "4. Remove duplicate information that appears across sections\n"
            "5. Ensure proper markdown formatting (tables, lists, emphasis)\n"
            "6. Create a natural flow that reads like a single document\n"
            "7. Maintain paragraph breaks and spacing for readability\n"
            "8. If the document has a clear title, make it the main heading\n\n"
            "Return ONLY the reconstructed markdown document with no additional commentary."
        )

        user_prompt = (
            "Below is text extracted from different sections of a document. "
            "Each section is labeled with its type and separated by markers. "
            "Please reconstruct this into a single, cohesive markdown document:\n\n"
            f"{sections_text}"
        )

        try:
            log.info("Sending extracted sections to VLM for reconstruction")

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=RECONSTRUCTION_MAX_TOKENS,
                temperature=RECONSTRUCTION_TEMPERATURE
            )

            reconstructed = (response.choices[0].message.content or "").strip()

            # Clean up any markdown code fence artifacts
            if reconstructed.startswith("```markdown"):
                reconstructed = reconstructed[len("```markdown"):].strip()
            if reconstructed.startswith("```"):
                reconstructed = reconstructed[3:].strip()
            if reconstructed.endswith("```"):
                reconstructed = reconstructed[:-3].strip()

            return reconstructed

        except Exception as e:
            log.error(f"Failed to reconstruct document: {e}")
            return f"# Reconstruction Failed\n\nError: {str(e)}\n\n## Original Sections\n\n{sections_text}"
