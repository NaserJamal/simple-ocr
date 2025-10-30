"""
PDF layout-based text extraction - detects sections and extracts text in parallel
"""

import os
import sys
import json
import logging
import pymupdf
from PIL import Image
import io

from image_processor import ImageProcessor
from section_detector import SectionDetector
from text_extractor import TextExtractor
from visualizer import SectionVisualizer
from config import OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Default PDF to process (relative to this script's directory)
DEFAULT_PDF = "../../PDF/1-page-text-img.pdf"


class LayoutTextExtractor:
    """Extracts text from PDF documents using layout-based section detection"""

    def __init__(self, pdf_path: str, output_dir: str = OUTPUT_DIR, max_workers: int = 5):
        """
        Initialize extractor

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory for output files
            max_workers: Maximum parallel text extraction tasks
        """
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.processor = ImageProcessor()
        self.detector = SectionDetector()
        self.text_extractor = TextExtractor(max_workers=max_workers)
        self.visualizer = SectionVisualizer()
        os.makedirs(self.output_dir, exist_ok=True)

    def process_document(self) -> dict:
        """Process entire PDF document and extract text"""
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
                        page_text = f"\n{'='*80}\nPAGE {page_num + 1}\n{'='*80}\n\n"
                        for section in page_result['sections']:
                            section_type = section.get('section_type', 'unknown')
                            text = section.get('text', '')
                            if text:
                                page_text += f"[{section_type.upper()}]\n{text}\n\n"
                        all_text_parts.append(page_text)

                except Exception as e:
                    log.error(f"Failed to process page {page_num}: {e}")
                    all_results.append({"page": page_num, "error": str(e), "sections": []})

            doc.close()

            # Save results
            self._save_json_results(all_results)
            self._save_text_results(all_text_parts)

            summary = self._generate_summary(all_results)
            log.info(f"Processing complete: {summary}")

            return {"success": True, "num_pages": num_pages, "results": all_results, "summary": summary}

        except Exception as e:
            log.error(f"Failed to process document: {e}")
            return {"success": False, "error": str(e)}

    def process_page(self, page: pymupdf.Page, page_num: int) -> dict:
        """Process a single PDF page"""
        # Convert page to image for detection
        img_base64, orig_width, orig_height, scale_x, scale_y = self.processor.process_page(page)

        # Detect layout sections
        sections = self.detector.detect_sections(img_base64, page_num)

        # Denormalize coordinates to original space
        denormalized_sections = []
        for section in sections:
            try:
                x0, y0, x1, y1 = self.processor.denormalize_coordinates(
                    section['rect'], orig_width, orig_height, scale_x, scale_y
                )
                denormalized_section = section.copy()
                denormalized_section['rect'] = [x0, y0, x1, y1]
                denormalized_sections.append(denormalized_section)
            except Exception as e:
                log.warning(f"Failed to denormalize section: {e}")

        # Get original page image for cropping
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1, 1), colorspace=pymupdf.csRGB)
        page_image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

        # Extract text from sections in parallel
        sections_with_text = self.text_extractor.extract_sections_parallel(
            page_image, denormalized_sections, page_num
        )

        # Create visualization
        self._create_visualization(page_image, denormalized_sections, page_num)

        return {
            "page": page_num,
            "sections": sections_with_text,
            "num_sections": len(sections_with_text),
            "image_dimensions": {"width": orig_width, "height": orig_height}
        }

    def _create_visualization(self, page_image: Image.Image, sections: list, page_num: int):
        """Create and save visualization for a page"""
        try:
            output_path = os.path.join(self.output_dir, f"page_{page_num + 1}_sections.png")
            self.visualizer.save_visualization(
                page_image, sections, output_path, show_labels=True, show_fill=False
            )
            log.info(f"Saved visualization: {output_path}")
        except Exception as e:
            log.error(f"Failed to create visualization for page {page_num}: {e}")

    def _save_json_results(self, results: list):
        """Save all results to JSON file"""
        try:
            output_path = os.path.join(self.output_dir, "sections.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            log.info(f"Saved JSON results to {output_path}")
        except Exception as e:
            log.error(f"Failed to save JSON results: {e}")

    def _save_text_results(self, text_parts: list):
        """Save extracted text to .txt file"""
        try:
            output_path = os.path.join(self.output_dir, "extracted_text.txt")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(text_parts))
            log.info(f"Saved extracted text to {output_path}")
        except Exception as e:
            log.error(f"Failed to save text results: {e}")

    def _generate_summary(self, results: list) -> dict:
        """Generate summary statistics"""
        section_types = {}
        total_chars = 0

        for result in results:
            for section in result.get('sections', []):
                section_type = section.get('section_type', 'unknown')
                section_types[section_type] = section_types.get(section_type, 0) + 1

                text = section.get('text', '')
                total_chars += len(text)

        return {
            "total_sections": sum(r.get('num_sections', 0) for r in results),
            "successful_pages": sum(1 for r in results if 'error' not in r),
            "failed_pages": sum(1 for r in results if 'error' in r),
            "section_types": section_types,
            "total_characters_extracted": total_chars
        }


def main():
    """Main entry point"""
    # Get PDF path from command line or use default
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF

    # Convert relative paths to absolute (relative to this script)
    if not os.path.isabs(pdf_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_path = os.path.join(script_dir, pdf_path)

    if not os.path.exists(pdf_path):
        log.error(f"PDF file not found: {pdf_path}")
        sys.exit(1)

    extractor = LayoutTextExtractor(pdf_path)
    result = extractor.process_document()

    if result['success']:
        s = result['summary']
        print(f"\n{'='*80}")
        print("LAYOUT-BASED TEXT EXTRACTION COMPLETE")
        print(f"{'='*80}")
        print(f"Pages processed: {result['num_pages']}")
        print(f"Total sections detected: {s['total_sections']}")
        print(f"Total characters extracted: {s['total_characters_extracted']}")
        print(f"Successful pages: {s['successful_pages']}")
        print(f"Failed pages: {s['failed_pages']}")
        print("\nSection types detected:")
        for section_type, count in sorted(s['section_types'].items()):
            print(f"  - {section_type}: {count}")
        print(f"\nResults saved to: {extractor.output_dir}")
        print(f"  - sections.json: Detailed section data with extracted text")
        print(f"  - extracted_text.txt: Combined extracted text")
        print(f"  - page_N_sections.png: Visualizations")
        print(f"{'='*80}")
    else:
        print(f"\nERROR: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
