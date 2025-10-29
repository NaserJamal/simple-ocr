"""
Main script for PDF layout detection
Processes PDF pages and generates layout visualizations
"""

import os
import sys
import json
import logging
from pathlib import Path
import pymupdf
from PIL import Image
import io

from image_processor import ImageProcessor
from layout_detector import LayoutDetector
from visualizer import LayoutVisualizer
from config import OUTPUT_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


class LayoutExtractor:
    """Main class for extracting layouts from PDF documents"""

    def __init__(self, pdf_path: str, output_dir: str = OUTPUT_DIR):
        """
        Initialize layout extractor

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory for output files
        """
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.processor = ImageProcessor()
        self.detector = LayoutDetector()
        self.visualizer = LayoutVisualizer()

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

    def process_document(self) -> dict:
        """
        Process entire PDF document and detect layouts

        Returns:
            Dictionary with processing results and statistics
        """
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
                    all_results.append({
                        "page": page_num,
                        "error": str(e),
                        "layouts": []
                    })

            doc.close()

            # Save combined results
            self._save_results(all_results)

            # Generate summary
            summary = self._generate_summary(all_results)
            log.info(f"Processing complete: {summary}")

            return {
                "success": True,
                "num_pages": num_pages,
                "results": all_results,
                "summary": summary
            }

        except Exception as e:
            log.error(f"Failed to process document: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def process_page(self, page: pymupdf.Page, page_num: int) -> dict:
        """
        Process a single PDF page

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)

        Returns:
            Dictionary with page processing results
        """
        # Step 1: Convert page to image
        img_base64, orig_width, orig_height, scale_x, scale_y = self.processor.process_page(page)

        # Step 2: Detect layouts
        layouts = self.detector.detect_layouts(img_base64, page_num)

        # Step 3: Denormalize coordinates back to original pixel space
        denormalized_layouts = []
        for layout in layouts:
            try:
                x0, y0, x1, y1 = self.processor.denormalize_coordinates(
                    layout['rect'],
                    orig_width,
                    orig_height,
                    scale_x,
                    scale_y
                )
                denormalized_layout = layout.copy()
                denormalized_layout['rect'] = [x0, y0, x1, y1]
                denormalized_layouts.append(denormalized_layout)
            except Exception as e:
                log.warning(f"Failed to denormalize layout: {e}")
                continue

        # Step 4: Create visualization
        self._create_visualization(page, denormalized_layouts, page_num)

        return {
            "page": page_num,
            "layouts": denormalized_layouts,
            "num_layouts": len(denormalized_layouts),
            "image_dimensions": {
                "width": orig_width,
                "height": orig_height
            }
        }

    def _create_visualization(self, page: pymupdf.Page, layouts: list, page_num: int):
        """Create and save visualization for a page"""
        try:
            # Render page to PIL Image
            pix = page.get_pixmap(matrix=pymupdf.Matrix(1, 1), colorspace=pymupdf.csRGB)
            img_bytes = pix.tobytes("png")
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

            # Create visualization
            output_path = os.path.join(self.output_dir, f"page_{page_num + 1}_layout.png")
            self.visualizer.save_visualization(
                pil_img,
                layouts,
                output_path,
                show_labels=True,
                show_fill=False
            )

            log.info(f"Saved visualization for page {page_num + 1}: {output_path}")

        except Exception as e:
            log.error(f"Failed to create visualization for page {page_num}: {e}")

    def _save_results(self, results: list):
        """Save all results to JSON file"""
        try:
            output_path = os.path.join(self.output_dir, "layouts.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            log.info(f"Saved results to {output_path}")
        except Exception as e:
            log.error(f"Failed to save results: {e}")

    def _generate_summary(self, results: list) -> dict:
        """Generate summary statistics"""
        total_layouts = sum(r.get('num_layouts', 0) for r in results)
        successful_pages = sum(1 for r in results if 'error' not in r)
        failed_pages = sum(1 for r in results if 'error' in r)

        # Count by layout type
        layout_types = {}
        for result in results:
            for layout in result.get('layouts', []):
                layout_type = layout.get('layout_type', 'unknown')
                layout_types[layout_type] = layout_types.get(layout_type, 0) + 1

        return {
            "total_layouts": total_layouts,
            "successful_pages": successful_pages,
            "failed_pages": failed_pages,
            "layout_types": layout_types
        }


def main():
    """Main entry point"""
    # Default PDF path (relative to this script)
    default_pdf = "../../PDF/application-form.pdf"

    # Allow PDF path as command line argument
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = default_pdf

    # Convert to absolute path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(script_dir, pdf_path)

    if not os.path.exists(pdf_path):
        log.error(f"PDF file not found: {pdf_path}")
        sys.exit(1)

    # Create extractor and process
    extractor = LayoutExtractor(pdf_path)
    result = extractor.process_document()

    if result['success']:
        print("\n" + "="*60)
        print("LAYOUT DETECTION COMPLETE")
        print("="*60)
        print(f"Pages processed: {result['num_pages']}")
        print(f"Total layouts detected: {result['summary']['total_layouts']}")
        print(f"Successful pages: {result['summary']['successful_pages']}")
        print(f"Failed pages: {result['summary']['failed_pages']}")
        print("\nLayout types detected:")
        for layout_type, count in sorted(result['summary']['layout_types'].items()):
            print(f"  - {layout_type}: {count}")
        print(f"\nResults saved to: {extractor.output_dir}")
        print("="*60)
    else:
        print(f"\nERROR: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
