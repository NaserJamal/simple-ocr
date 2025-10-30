"""PDF layout-based text extraction - detects sections and extracts text in parallel."""

import io
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import pymupdf
from PIL import Image

from utils.config import OUTPUT_DIR
from utils.extraction_manager import ExtractionManager
from utils.image_processor import ImageProcessor
from utils.section_detector import SectionDetector
from utils.text_extractor import TextExtractor
from utils.visualizer import SectionVisualizer
import utils.interactive_menu as menu

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

DEFAULT_PDF = "../../PDF/form-field-example-2.pdf"


class LayoutTextExtractor:
    """Extracts text from PDF documents using layout-based section detection."""

    def __init__(
        self,
        pdf_path: str,
        output_dir: str = OUTPUT_DIR,
        max_workers: int = 5,
        section_request: Optional[str] = None,
        extraction_id: Optional[str] = None,
    ) -> None:
        """Initialize extractor with PDF path and output directory.

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory for output files
            max_workers: Number of parallel workers for text extraction
            section_request: User's natural language description of section to extract
            extraction_id: Optional UUID for this extraction (auto-generated if None)
        """
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.section_request = section_request

        # Initialize extraction manager
        extraction_id = extraction_id or str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        self.manager = ExtractionManager(output_dir, extraction_id, timestamp)

        # Core processors
        self.processor = ImageProcessor()
        self.detector = SectionDetector(section_request=section_request)
        self.text_extractor = TextExtractor(max_workers=max_workers, section_request=section_request)
        self.visualizer = SectionVisualizer()

        log.info(f"Extraction ID: {self.manager.extraction_id[:8]}")

    def process_document(self) -> Dict:
        """Process entire PDF document and extract text."""
        log.info(f"Processing PDF: {self.pdf_path}")

        try:
            doc = pymupdf.open(self.pdf_path)
            num_pages = len(doc)
            log.info(f"Document has {num_pages} pages")

            all_results = []
            all_text_parts = []

            for page_num, page in enumerate(doc):
                log.info(f"Processing page {page_num + 1}/{num_pages}")
                try:
                    page_result = self.process_page(page, page_num)
                    all_results.append(page_result)

                    # Collect text for combined output
                    if 'sections' in page_result:
                        page_text = f"\n{'=' * 80}\nPAGE {page_num + 1}\n{'=' * 80}\n\n"
                        for section in page_result['sections']:
                            text = section.get('text', '')
                            if text:
                                section_type = section.get('section_type', 'unknown').upper()
                                page_text += f"[{section_type}]\n{text}\n\n"
                        all_text_parts.append(page_text)

                except Exception as e:
                    log.error(f"Failed to process page {page_num}: {e}")
                    all_results.append({"page": page_num, "error": str(e), "sections": []})

            doc.close()

            # Save results and update index
            self.manager.save_json_results(all_results)
            self.manager.save_text_results(all_text_parts)
            self.manager.update_extraction_index(all_results, self.pdf_path, self.section_request)

            summary = self.manager._generate_summary(all_results)
            log.info(f"Processing complete: {summary}")

            return {
                "success": True,
                "extraction_id": self.manager.extraction_id,
                "extraction_dir": self.manager.extraction_dir,
                "num_pages": num_pages,
                "results": all_results,
                "summary": summary,
            }

        except Exception as e:
            log.error(f"Failed to process document: {e}")
            return {"success": False, "error": str(e)}

    def process_page(self, page: pymupdf.Page, page_num: int) -> Dict:
        """Process a single PDF page."""
        img_base64, orig_width, orig_height, scale_x, scale_y = self.processor.process_page(page)
        sections = self.detector.detect_sections(img_base64, page_num)

        # Denormalize coordinates to original space
        denormalized_sections = [
            {
                **section,
                'rect': list(
                    self.processor.denormalize_coordinates(
                        section['rect'], orig_width, orig_height, scale_x, scale_y
                    )
                ),
            }
            for section in sections
        ]

        # Get original page image for cropping
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1, 1), colorspace=pymupdf.csRGB)
        page_image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

        # Extract text from sections in parallel
        sections_with_text = self.text_extractor.extract_sections_parallel(
            page_image, denormalized_sections, page_num
        )

        self._create_visualization(page_image, denormalized_sections, page_num)

        return {
            "page": page_num,
            "sections": sections_with_text,
            "num_sections": len(sections_with_text),
            "image_dimensions": {"width": orig_width, "height": orig_height},
        }

    def _create_visualization(
        self, page_image: Image.Image, sections: List[Dict], page_num: int
    ) -> None:
        """Create and save visualization for a page."""
        output_path = os.path.join(self.manager.extraction_dir, f"page_{page_num + 1}_sections.png")
        self.visualizer.save_visualization(
            page_image, sections, output_path, show_labels=True, show_fill=False
        )
        log.info(f"Saved visualization: {output_path}")

    def extract_from_cached_section(self, section_indices: List[int]) -> Dict:
        """Re-extract text from specific cached sections with new user prompt.

        Note: This does NOT add to the extraction index since we're not detecting
        new sections, just re-processing existing ones.
        """
        cached_data = ExtractionManager.load_latest_cached_sections(self.output_dir)
        if not cached_data:
            return {"success": False, "error": "No cached sections found"}

        try:
            doc = pymupdf.open(self.pdf_path)
            results = []

            for page_data in cached_data:
                page_num = page_data['page']
                page = doc[page_num]

                # Get original page image
                pix = page.get_pixmap(matrix=pymupdf.Matrix(1, 1), colorspace=pymupdf.csRGB)
                page_image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

                # Filter sections by requested indices
                selected_sections = [
                    s for s in page_data['sections']
                    if s.get('index') in section_indices
                ]

                if selected_sections:
                    # Re-extract text with current section_request context
                    sections_with_text = self.text_extractor.extract_sections_parallel(
                        page_image, selected_sections, page_num
                    )
                    results.append({
                        "page": page_num,
                        "sections": sections_with_text,
                        "num_sections": len(sections_with_text)
                    })

            doc.close()

            # Save results (but don't update index - these aren't new sections)
            self.manager.save_json_results(results)
            text_parts = []
            for page_result in results:
                page_text = f"\n{'='*80}\nPAGE {page_result['page'] + 1}\n{'='*80}\n\n"
                for section in page_result['sections']:
                    text = section.get('text', '')
                    if text:
                        page_text += f"[{section.get('section_type', 'unknown').upper()}]\n{text}\n\n"
                text_parts.append(page_text)
            self.manager.save_text_results(text_parts)

            summary = self.manager._generate_summary(results)
            return {
                "success": True,
                "extraction_id": self.manager.extraction_id,
                "extraction_dir": self.manager.extraction_dir,
                "results": results,
                "summary": summary,
                "is_reextraction": True  # Flag to indicate this was a re-extraction
            }

        except Exception as e:
            log.error(f"Failed to extract from cached sections: {e}")
            return {"success": False, "error": str(e)}


def run_interactive_mode(pdf_path: str, output_dir: str, index_path: str) -> Dict:
    """Run interactive mode with user prompts."""
    menu.display_welcome_banner(os.path.basename(pdf_path))

    # Check if there's extraction history
    has_history = os.path.exists(index_path)
    use_existing = False

    if has_history:
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
                if index:
                    mode_choice = menu.prompt_mode_selection(True)
                    use_existing = (mode_choice == 'existing')
                else:
                    has_history = False
        except Exception as e:
            log.warning(f"Failed to load extraction index: {e}")
            has_history = False

    # If user wants to use existing sections
    if use_existing:
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)

        all_sections = menu.load_all_previous_sections(output_dir, index)

        if not all_sections:
            print("Error: Could not load any previous sections. Starting new extraction.")
        else:
            selection = menu.display_sections_menu(all_sections)
            if selection is None:
                sys.exit(1)

            section_request = menu.prompt_extraction_context_for_cached()
            extractor = LayoutTextExtractor(pdf_path, output_dir=output_dir, section_request=section_request)

            # Extract indices from the nested structure
            section_indices = [item['section']['index'] for item in selection['sections']]

            return extractor.extract_from_cached_section(section_indices)

    # New extraction
    section_request = menu.prompt_section_request_for_new()
    if section_request:
        log.info(f"User requested: '{section_request}'")

    extractor = LayoutTextExtractor(pdf_path, output_dir=output_dir, section_request=section_request)
    return extractor.process_document()


def run_command_line_mode(pdf_path: str, output_dir: str, section_request: Optional[str]) -> Dict:
    """Run command-line mode with provided section request."""
    if section_request:
        log.info(f"User requested: '{section_request}'")

    extractor = LayoutTextExtractor(pdf_path, output_dir=output_dir, section_request=section_request)
    return extractor.process_document()


def main() -> None:
    """Main entry point."""
    # Parse command line arguments
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    section_request = sys.argv[2] if len(sys.argv) > 2 else None

    # Resolve PDF path
    if not os.path.isabs(pdf_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_path = os.path.join(script_dir, pdf_path)

    if not os.path.exists(pdf_path):
        log.error(f"PDF file not found: {pdf_path}")
        sys.exit(1)

    # Setup paths
    output_dir = OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    index_path = os.path.join(output_dir, "extraction_index.json")

    # Run appropriate mode
    if section_request is None:
        result = run_interactive_mode(pdf_path, output_dir, index_path)
    else:
        result = run_command_line_mode(pdf_path, output_dir, section_request)

    # Display results
    display_dir = result.get('extraction_dir', output_dir)
    success = menu.display_results_summary(result, display_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
