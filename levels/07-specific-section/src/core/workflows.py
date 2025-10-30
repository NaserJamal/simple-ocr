"""Workflows for different extraction modes."""

import json
import logging
import os
import sys
from typing import Dict, Optional

from src.core.extractor import LayoutTextExtractor
import src.ui.interactive_menu as menu

log = logging.getLogger(__name__)


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
