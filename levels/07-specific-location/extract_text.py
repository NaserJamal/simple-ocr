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
DEFAULT_PDF = "../../PDF/form-field-example.pdf"


class LayoutTextExtractor:
    """Extracts text from PDF documents using layout-based section detection"""

    def __init__(self, pdf_path: str, output_dir: str = OUTPUT_DIR, max_workers: int = 5, section_request: str = None):
        """Initialize extractor with PDF path and output directory

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory for output files
            max_workers: Number of parallel workers for text extraction
            section_request: User's natural language description of section to extract (e.g., "extract the notes section")
        """
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.section_request = section_request
        self.processor = ImageProcessor()
        self.detector = SectionDetector(section_request=section_request)
        self.text_extractor = TextExtractor(max_workers=max_workers, section_request=section_request)
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
                            text = section.get('text', '')
                            if text:
                                page_text += f"[{section.get('section_type', 'unknown').upper()}]\n{text}\n\n"
                        all_text_parts.append(page_text)

                except Exception as e:
                    log.error(f"Failed to process page {page_num}: {e}")
                    all_results.append({"page": page_num, "error": str(e), "sections": []})

            doc.close()

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

        # Extract text from sections in parallel
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

    def _load_cached_sections(self) -> list:
        """Load previously detected sections from cache file"""
        cache_path = os.path.join(self.output_dir, "sections.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                log.warning(f"Failed to load cached sections: {e}")
        return None

    def extract_from_cached_section(self, section_indices: list) -> dict:
        """Re-extract text from specific cached sections with new user prompt"""
        cached_data = self._load_cached_sections()
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

            # Save results
            self._save_json_results(results)
            text_parts = []
            for page_result in results:
                page_text = f"\n{'='*80}\nPAGE {page_result['page'] + 1}\n{'='*80}\n\n"
                for section in page_result['sections']:
                    text = section.get('text', '')
                    if text:
                        page_text += f"[{section.get('section_type', 'unknown').upper()}]\n{text}\n\n"
                text_parts.append(page_text)
            self._save_text_results(text_parts)

            summary = self._generate_summary(results)
            return {"success": True, "results": results, "summary": summary}

        except Exception as e:
            log.error(f"Failed to extract from cached sections: {e}")
            return {"success": False, "error": str(e)}

    def _save_text_results(self, text_parts: list):
        """Save extracted text to .txt file"""
        output_path = os.path.join(self.output_dir, "extracted_text.txt")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(text_parts))
        log.info(f"Saved extracted text to {output_path}")

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


def display_sections_menu(cached_data: list) -> dict:
    """Display cached sections and let user choose which to extract"""
    print("\n" + "="*80)
    print("AVAILABLE SECTIONS")
    print("="*80)

    all_sections = []
    for page_data in cached_data:
        page_num = page_data['page']
        for section in page_data['sections']:
            idx = section.get('index', -1)
            section_type = section.get('section_type', 'unknown')
            text_preview = section.get('text', '')[:50]
            all_sections.append({
                'page': page_num,
                'index': idx,
                'section_type': section_type,
                'text_preview': text_preview,
                'section_data': section
            })

    # Display sections
    for i, sec in enumerate(all_sections, 1):
        print(f"\n[{i}] Page {sec['page'] + 1} - {sec['section_type'].replace('_', ' ').title()}")
        if sec['text_preview']:
            print(f"    Preview: {sec['text_preview']}...")

    print("\n" + "-"*80)
    print("Enter section numbers to extract (comma-separated, e.g., '1,3,5')")
    print("Or press Enter to extract all sections")
    print("-"*80)

    user_input = input("Your choice: ").strip()

    if not user_input:
        # Extract all
        return {'mode': 'all', 'sections': all_sections}

    try:
        selected_nums = [int(x.strip()) for x in user_input.split(',')]
        selected_sections = []
        for num in selected_nums:
            if 1 <= num <= len(all_sections):
                selected_sections.append(all_sections[num - 1])
            else:
                print(f"Warning: Section {num} is out of range, skipping...")

        return {'mode': 'selected', 'sections': selected_sections}
    except ValueError:
        print("Invalid input. Please enter numbers separated by commas.")
        return None


def main():
    """Main entry point"""
    # Parse command line arguments
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    section_request = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.isabs(pdf_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_path = os.path.join(script_dir, pdf_path)

    if not os.path.exists(pdf_path):
        log.error(f"PDF file not found: {pdf_path}")
        sys.exit(1)

    # Check for cached sections
    output_dir = OUTPUT_DIR
    cache_path = os.path.join(output_dir, "sections.json")
    has_cache = os.path.exists(cache_path)

    # Interactive mode
    if section_request is None:
        print("\n" + "="*80)
        print("SPECIFIC LOCATION TEXT EXTRACTION")
        print("="*80)
        print(f"\nPDF: {os.path.basename(pdf_path)}")

        mode_choice = None
        if has_cache:
            print("\n" + "-"*80)
            print("Choose a mode:")
            print("  [1] Use existing sections (from previous detection)")
            print("  [2] Identify new sections (detect layout again)")
            print("-"*80)
            mode_input = input("Your choice (1 or 2): ").strip()

            if mode_input == '1':
                mode_choice = 'existing'
            elif mode_input == '2':
                mode_choice = 'new'
            else:
                print("Invalid choice. Defaulting to new section detection.")
                mode_choice = 'new'
        else:
            mode_choice = 'new'

        if mode_choice == 'existing':
            # Load and display cached sections
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            selection = display_sections_menu(cached_data)
            if selection is None:
                sys.exit(1)

            # Ask for extraction context
            print("\n" + "="*80)
            print("What do you want to extract from these sections?")
            print("Examples:")
            print("  - 'extract the notes'")
            print("  - 'find contact information'")
            print("  - Press Enter to extract all text as-is")
            print("-"*80)
            section_request = input("Your request: ").strip() or None

            if section_request:
                print(f"\nExtracting: '{section_request}'")
            print("="*80 + "\n")

            # Extract from selected cached sections
            extractor = LayoutTextExtractor(pdf_path, section_request=section_request)

            if selection['mode'] == 'all':
                section_indices = [s['index'] for s in selection['sections']]
            else:
                section_indices = [s['index'] for s in selection['sections']]

            result = extractor.extract_from_cached_section(section_indices)

        else:  # mode_choice == 'new'
            print("\n" + "-"*80)
            print("What section would you like to extract?")
            print("Examples:")
            print("  - 'extract the notes section'")
            print("  - 'find the summary'")
            print("  - 'get the contact information'")
            print("  - Press Enter to detect and extract ALL sections")
            print("-"*80)

            user_input = input("Your request: ").strip()

            if user_input:
                section_request = user_input
                print(f"\nExtracting: '{section_request}'")
            else:
                print("\nDetecting all sections (default mode)")
            print("="*80 + "\n")

            extractor = LayoutTextExtractor(pdf_path, section_request=section_request)
            result = extractor.process_document()

    else:
        # Command-line mode with section request provided
        if section_request:
            log.info(f"User requested: '{section_request}'")

        extractor = LayoutTextExtractor(pdf_path, section_request=section_request)
        result = extractor.process_document()

    if result['success']:
        s = result['summary']
        print(f"\n{'='*80}")
        print("LAYOUT-BASED TEXT EXTRACTION COMPLETE")
        print(f"{'='*80}")

        # num_pages only exists for full document processing
        if 'num_pages' in result:
            print(f"Pages processed: {result['num_pages']}")

        print(f"Total sections extracted: {s['total_sections']}")
        print(f"Total characters extracted: {s['total_characters_extracted']}")
        print(f"Successful pages: {s['successful_pages']}")
        print(f"Failed pages: {s['failed_pages']}")
        print("\nSection types detected:")
        for section_type, count in sorted(s['section_types'].items()):
            print(f"  - {section_type}: {count}")
        print(f"\nResults saved to: {output_dir}")
        print(f"  - sections.json: Detailed section data with extracted text")
        print(f"  - extracted_text.txt: Combined extracted text")

        # Visualizations only for full document processing
        if 'num_pages' in result:
            print(f"  - page_N_sections.png: Visualizations")
        print(f"{'='*80}")
    else:
        print(f"\nERROR: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
