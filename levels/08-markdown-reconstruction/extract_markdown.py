"""
PDF markdown reconstruction - detects sections, extracts text as markdown, and reconstructs
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
from markdown_reconstructor import MarkdownReconstructor
from visualizer import SectionVisualizer
from config import OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Default PDF to process (relative to this script's directory)
DEFAULT_PDF = "../../PDF/1-page-text-img.pdf"


class MarkdownExtractor:
    """Extracts text from PDF documents as markdown and reconstructs into cohesive document"""

    def __init__(self, pdf_path: str, output_dir: str = OUTPUT_DIR, max_workers: int = 5):
        """Initialize extractor with PDF path and output directory"""
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.processor = ImageProcessor()
        self.detector = SectionDetector()
        self.text_extractor = TextExtractor(max_workers=max_workers)
        self.reconstructor = MarkdownReconstructor()
        self.visualizer = SectionVisualizer()
        os.makedirs(self.output_dir, exist_ok=True)

    def process_document(self) -> dict:
        """Process entire PDF document and extract text as markdown"""
        log.info(f"Processing PDF: {self.pdf_path}")

        try:
            doc = pymupdf.open(self.pdf_path)
            num_pages = len(doc)
            log.info(f"Document has {num_pages} pages")

            all_results = []

            for page_num, page in enumerate(doc):
                log.info(f"Processing page {page_num + 1}/{num_pages}")
                try:
                    page_result = self.process_page(page, page_num)
                    all_results.append(page_result)

                except Exception as e:
                    log.error(f"Failed to process page {page_num}: {e}")
                    all_results.append({"page": page_num, "error": str(e), "sections": []})

            doc.close()

            # Save individual sections as JSON
            self._save_json_results(all_results)

            # Reconstruct into cohesive markdown
            log.info("Starting document reconstruction...")
            reconstructed_markdown = self.reconstructor.reconstruct_document(all_results)
            self._save_markdown_results(reconstructed_markdown)

            summary = self._generate_summary(all_results)
            log.info(f"Processing complete: {summary}")

            return {
                "success": True,
                "num_pages": num_pages,
                "results": all_results,
                "reconstructed_markdown": reconstructed_markdown,
                "summary": summary
            }

        except Exception as e:
            log.error(f"Failed to process document: {e}")
            return {"success": False, "error": str(e)}

    def process_page(self, page: pymupdf.Page, page_num: int) -> dict:
        """Process a single PDF page"""
        img_base64, orig_width, orig_height, scale_x, scale_y = self.processor.process_page(page)
        sections = self.detector.detect_sections(img_base64, page_num)

        # Denormalize coordinates to original space
        denormalized_sections = [
            {**section, 'rect': list(self.processor.denormalize_coordinates(
                section['rect'], orig_width, orig_height, scale_x, scale_y
            ))}
            for section in sections
        ]

        # Get original page image for cropping
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1, 1), colorspace=pymupdf.csRGB)
        page_image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

        # Extract text from sections in parallel (as markdown)
        sections_with_text = self.text_extractor.extract_sections_parallel(
            page_image, denormalized_sections, page_num
        )

        self._create_visualization(page_image, denormalized_sections, page_num)

        return {
            "page": page_num,
            "sections": sections_with_text,
            "num_sections": len(sections_with_text),
            "image_dimensions": {"width": orig_width, "height": orig_height}
        }

    def _create_visualization(self, page_image: Image.Image, sections: list, page_num: int):
        """Create and save visualization for a page"""
        output_path = os.path.join(self.output_dir, f"page_{page_num + 1}_sections.png")
        self.visualizer.save_visualization(page_image, sections, output_path, show_labels=True, show_fill=False)
        log.info(f"Saved visualization: {output_path}")

    def _save_json_results(self, results: list):
        """Save all results to JSON file"""
        output_path = os.path.join(self.output_dir, "sections.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        log.info(f"Saved JSON results to {output_path}")

    def _save_markdown_results(self, markdown: str):
        """Save reconstructed markdown to .md file"""
        output_path = os.path.join(self.output_dir, "reconstructed.md")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        log.info(f"Saved reconstructed markdown to {output_path}")

    def _generate_summary(self, results: list) -> dict:
        """Generate summary statistics"""
        section_types = {}
        total_chars = 0

        for result in results:
            for section in result.get('sections', []):
                section_type = section.get('section_type', 'unknown')
                section_types[section_type] = section_types.get(section_type, 0) + 1
                total_chars += len(section.get('text', ''))

        return {
            "total_sections": sum(r.get('num_sections', 0) for r in results),
            "successful_pages": sum(1 for r in results if 'error' not in r),
            "failed_pages": sum(1 for r in results if 'error' in r),
            "section_types": section_types,
            "total_characters_extracted": total_chars
        }


def main():
    """Main entry point"""
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF

    if not os.path.isabs(pdf_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_path = os.path.join(script_dir, pdf_path)

    if not os.path.exists(pdf_path):
        log.error(f"PDF file not found: {pdf_path}")
        sys.exit(1)

    extractor = MarkdownExtractor(pdf_path)
    result = extractor.process_document()

    if result['success']:
        s = result['summary']
        print(f"\n{'='*80}")
        print("MARKDOWN RECONSTRUCTION COMPLETE")
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
        print(f"  - reconstructed.md: Final reconstructed markdown document")
        print(f"  - sections.json: Detailed section data with extracted markdown")
        print(f"  - page_N_sections.png: Visualizations")
        print(f"{'='*80}")
    else:
        print(f"\nERROR: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
