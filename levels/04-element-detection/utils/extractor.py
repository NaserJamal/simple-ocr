"""PDF element detection - processes PDF pages and generates element visualizations"""

import os
import sys
import json
import logging
import pymupdf
from PIL import Image
import io

from .image_processor import ImageProcessor
from .element_detector import ElementDetector
from .visualizer import ElementVisualizer
from .config import OUTPUT_DIR

log = logging.getLogger(__name__)


class ElementExtractor:
    """Extracts elements from PDF documents"""

    def __init__(self, pdf_path: str, output_dir: str = OUTPUT_DIR):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.processor = ImageProcessor()
        self.detector = ElementDetector()
        self.visualizer = ElementVisualizer()
        os.makedirs(self.output_dir, exist_ok=True)

    def process_document(self) -> dict:
        """Process entire PDF document and detect elements"""
        log.info(f"Processing PDF: {self.pdf_path}")

        try:
            doc = pymupdf.open(self.pdf_path)
            num_pages = len(doc)
            log.info(f"Document has {num_pages} pages")

            all_results = []
            for page_num, page in enumerate(doc):
                log.info(f"Processing page {page_num + 1}/{num_pages}")
                try:
                    all_results.append(self.process_page(page, page_num))
                except Exception as e:
                    log.error(f"Failed to process page {page_num}: {e}")
                    all_results.append({"page": page_num, "error": str(e), "elements": []})

            doc.close()
            self._save_results(all_results)
            summary = self._generate_summary(all_results)
            log.info(f"Processing complete: {summary}")

            return {"success": True, "num_pages": num_pages, "results": all_results, "summary": summary}

        except Exception as e:
            log.error(f"Failed to process document: {e}")
            return {"success": False, "error": str(e)}

    def process_page(self, page: pymupdf.Page, page_num: int) -> dict:
        """Process a single PDF page"""
        img_base64, orig_width, orig_height, scale_x, scale_y = self.processor.process_page(page)
        elements = self.detector.detect_elements(img_base64, page_num)

        denormalized_elements = []
        for element in elements:
            try:
                x0, y0, x1, y1 = self.processor.denormalize_coordinates(element['rect'], orig_width, orig_height, scale_x, scale_y)
                denormalized_element = element.copy()
                denormalized_element['rect'] = [x0, y0, x1, y1]
                denormalized_elements.append(denormalized_element)
            except Exception as e:
                log.warning(f"Failed to denormalize element: {e}")

        self._create_visualization(page, denormalized_elements, page_num)

        return {
            "page": page_num,
            "elements": denormalized_elements,
            "num_elements": len(denormalized_elements),
            "image_dimensions": {"width": orig_width, "height": orig_height}
        }

    def _create_visualization(self, page: pymupdf.Page, elements: list, page_num: int):
        """Create and save visualization for a page"""
        try:
            pix = page.get_pixmap(matrix=pymupdf.Matrix(1, 1), colorspace=pymupdf.csRGB)
            pil_img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            output_path = os.path.join(self.output_dir, f"page_{page_num + 1}_elements.png")
            self.visualizer.save_visualization(pil_img, elements, output_path, show_labels=True, show_fill=False)
            log.info(f"Saved visualization: {output_path}")
        except Exception as e:
            log.error(f"Failed to create visualization for page {page_num}: {e}")

    def _save_results(self, results: list):
        """Save all results to JSON file"""
        try:
            output_path = os.path.join(self.output_dir, "elements.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            log.info(f"Saved results to {output_path}")
        except Exception as e:
            log.error(f"Failed to save results: {e}")

    def _generate_summary(self, results: list) -> dict:
        """Generate summary statistics"""
        element_types = {}
        for result in results:
            for element in result.get('elements', []):
                element_type = element.get('layout_type', 'unknown')
                element_types[element_type] = element_types.get(element_type, 0) + 1

        return {
            "total_elements": sum(r.get('num_elements', 0) for r in results),
            "successful_pages": sum(1 for r in results if 'error' not in r),
            "failed_pages": sum(1 for r in results if 'error' in r),
            "element_types": element_types
        }
