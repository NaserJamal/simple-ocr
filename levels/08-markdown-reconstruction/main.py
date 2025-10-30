"""
Markdown Reconstruction System

Main entry point for extracting text from PDFs as markdown and reconstructing
into cohesive, well-formatted documents.

Usage:
    python main.py                    # Process default PDF
    python main.py path/to/file.pdf   # Process specific PDF
"""

import os
import sys
import logging

from utils import MarkdownExtractor, OUTPUT_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Default PDF to process (relative to this script's directory)
DEFAULT_PDF = "../../PDF/1-page-text-img.pdf"


def main():
    """Main entry point for markdown reconstruction"""

    # Get PDF path from command line or use default
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF

    # Convert to absolute path if relative
    if not os.path.isabs(pdf_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_path = os.path.join(script_dir, pdf_path)

    # Check if PDF exists
    if not os.path.exists(pdf_path):
        log.error(f"PDF file not found: {pdf_path}")
        sys.exit(1)

    # Create extractor and process document
    log.info(f"Starting markdown extraction for: {pdf_path}")
    extractor = MarkdownExtractor(pdf_path)
    result = extractor.process_document()

    # Display results
    if result['success']:
        print_success_summary(result, extractor.output_dir)
    else:
        log.error(f"Processing failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


def print_success_summary(result: dict, output_dir: str):
    """Print formatted success summary"""
    summary = result['summary']

    print(f"\n{'='*80}")
    print("MARKDOWN RECONSTRUCTION COMPLETE")
    print(f"{'='*80}")
    print(f"Pages processed: {result['num_pages']}")
    print(f"Total sections detected: {summary['total_sections']}")
    print(f"Total characters extracted: {summary['total_characters_extracted']}")
    print(f"Successful pages: {summary['successful_pages']}")
    print(f"Failed pages: {summary['failed_pages']}")

    print("\nSection types detected:")
    for section_type, count in sorted(summary['section_types'].items()):
        print(f"  - {section_type}: {count}")

    print(f"\nResults saved to: {output_dir}")
    print(f"  - reconstructed.md: Final reconstructed markdown document")
    print(f"  - sections.json: Detailed section data with extracted markdown")
    print(f"  - page_N_sections.png: Visualizations")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
