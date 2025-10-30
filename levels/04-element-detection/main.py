#!/usr/bin/env python3
"""
Element Detection System - Main Entry Point

Processes PDF documents to detect and visualize structural elements
(paragraphs, headings, tables, images, etc.) using Vision Language Models.

Usage:
    python main.py                          # Uses default PDF
    python main.py /path/to/document.pdf    # Uses specified PDF
"""

import sys
import os
import logging

from utils.extractor import ElementExtractor
from utils.config import OUTPUT_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Default PDF path (relative to this script)
DEFAULT_PDF = "../../PDF/cv-example.pdf"


def main():
    """Main entry point for element detection system"""

    # Get PDF path from command line or use default
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF

    # Convert relative paths to absolute
    if not os.path.isabs(pdf_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_path = os.path.join(script_dir, pdf_path)

    # Validate PDF exists
    if not os.path.exists(pdf_path):
        log.error(f"PDF file not found: {pdf_path}")
        sys.exit(1)

    # Create extractor and process document
    extractor = ElementExtractor(pdf_path)
    result = extractor.process_document()

    # Display results
    if result['success']:
        print_success_summary(result, extractor.output_dir)
    else:
        print_error_message(result)
        sys.exit(1)


def print_success_summary(result: dict, output_dir: str):
    """Print formatted success summary"""
    summary = result['summary']

    print(f"\n{'='*60}")
    print("ELEMENT DETECTION COMPLETE")
    print(f"{'='*60}")
    print(f"Pages processed: {result['num_pages']}")
    print(f"Total elements detected: {summary['total_elements']}")
    print(f"Successful pages: {summary['successful_pages']}")
    print(f"Failed pages: {summary['failed_pages']}")

    print("\nElement types detected:")
    for element_type, count in sorted(summary['element_types'].items()):
        print(f"  - {element_type}: {count}")

    print(f"\nResults saved to: {output_dir}")
    print(f"{'='*60}")


def print_error_message(result: dict):
    """Print formatted error message"""
    print(f"\nERROR: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
