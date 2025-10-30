"""Main entry point for PDF layout-based text extraction."""

import logging
import os
import sys

from src.infrastructure.config import OUTPUT_DIR
from src.core.workflows import run_interactive_mode, run_command_line_mode
import src.ui.interactive_menu as menu

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

DEFAULT_PDF = "../../PDF/form-field-example-2.pdf"


def main() -> None:
    """Main entry point."""
    # Parse command line arguments
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    section_request = sys.argv[2] if len(sys.argv) > 2 else None

    # Resolve PDF path
    if not os.path.isabs(pdf_path):
        # Get project root (parent of src directory)
        src_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(src_dir)
        pdf_path = os.path.join(project_root, pdf_path)

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
