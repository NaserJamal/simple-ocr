"""Interactive menu system for user interaction."""

import json
import os
from typing import Dict, List, Optional, Tuple


def display_welcome_banner(pdf_name: str) -> None:
    """Display welcome banner with PDF name."""
    print("\n" + "=" * 80)
    print("SPECIFIC LOCATION TEXT EXTRACTION")
    print("=" * 80)
    print(f"\nPDF: {pdf_name}")


def load_all_previous_sections(output_dir: str, index: List[Dict]) -> List[Dict]:
    """Load and combine all sections from all previous extractions.

    Args:
        output_dir: Base output directory
        index: List of extraction metadata

    Returns:
        Combined list of all sections with extraction metadata
    """
    all_sections = []

    for entry in index:
        extraction_dir = os.path.join(output_dir, entry['extraction_dir'])
        sections_path = os.path.join(extraction_dir, 'sections.json')

        if os.path.exists(sections_path):
            try:
                with open(sections_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)

                # Add extraction metadata to each section
                for page_data in cached_data:
                    for section in page_data['sections']:
                        all_sections.append({
                            'page': page_data['page'],
                            'section': section,
                            'extraction_timestamp': entry['timestamp'][:19].replace('T', ' '),
                            'extraction_request': entry.get('section_request') or 'Full document'
                        })
            except Exception as e:
                print(f"Warning: Could not load sections from {entry['extraction_dir']}: {e}")

    return all_sections


def prompt_mode_selection(has_cache: bool) -> str:
    """Prompt user to choose between existing sections or new detection.

    Returns:
        'existing' or 'new'
    """
    if not has_cache:
        return 'new'

    print("\n" + "-" * 80)
    print("Choose a mode:")
    print("  [1] Use existing sections (from previous detection)")
    print("  [2] Identify new sections (detect layout again)")
    print("-" * 80)

    mode_input = input("Your choice (1 or 2): ").strip()

    if mode_input == '1':
        return 'existing'
    elif mode_input == '2':
        return 'new'
    else:
        print("Invalid choice. Defaulting to new section detection.")
        return 'new'


def display_sections_menu(all_sections: List[Dict]) -> Optional[Dict]:
    """Display all available sections and let user choose which to extract.

    Args:
        all_sections: List of section data from all extractions

    Returns:
        Dictionary with 'mode' and 'sections' keys, or None on error
    """
    print("\n" + "=" * 80)
    print("AVAILABLE SECTIONS (from all previous extractions)")
    print("=" * 80)

    # Display sections
    for i, item in enumerate(all_sections, 1):
        section = item['section']
        section_type = section.get('section_type', 'unknown')
        text_preview = section.get('text', '')[:50]
        timestamp = item['extraction_timestamp']

        print(f"\n[{i}] {section_type.replace('_', ' ').title()} - Page {item['page'] + 1}")
        print(f"    From: {timestamp}")
        if text_preview:
            print(f"    Preview: {text_preview}...")

    print("\n" + "-" * 80)
    print("Enter section numbers to extract (comma-separated, e.g., '1,3,5')")
    print("Or press Enter to extract all sections")
    print("-" * 80)

    user_input = input("Your choice: ").strip()

    if not user_input:
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


def prompt_extraction_context_for_cached() -> Optional[str]:
    """Prompt user for extraction context when using cached sections.

    Returns:
        User's extraction request or None
    """
    print("\n" + "=" * 80)
    print("What do you want to extract from these sections?")
    print("Examples:")
    print("  - 'extract the notes'")
    print("  - 'find contact information'")
    print("  - Press Enter to extract all text as-is")
    print("-" * 80)

    section_request = input("Your request: ").strip() or None

    if section_request:
        print(f"\nExtracting: '{section_request}'")
    print("=" * 80 + "\n")

    return section_request


def prompt_section_request_for_new() -> Optional[str]:
    """Prompt user for section request when detecting new sections.

    Returns:
        User's section request or None
    """
    print("\n" + "-" * 80)
    print("What section would you like to extract?")
    print("Examples:")
    print("  - 'extract the notes section'")
    print("  - 'find the summary'")
    print("  - 'get the contact information'")
    print("  - Press Enter to detect and extract ALL sections")
    print("-" * 80)

    user_input = input("Your request: ").strip()

    if user_input:
        print(f"\nExtracting: '{user_input}'")
    else:
        print("\nDetecting all sections (default mode)")
    print("=" * 80 + "\n")

    return user_input or None


def display_results_summary(result: Dict, output_dir: str) -> bool:
    """Display extraction results summary.

    Args:
        result: Result dictionary from extraction
        output_dir: Output directory path

    Returns:
        True if successful, False otherwise
    """
    if not result.get('success'):
        print(f"\nERROR: {result.get('error', 'Unknown error')}")
        return False

    s = result['summary']
    print(f"\n{'=' * 80}")
    print("LAYOUT-BASED TEXT EXTRACTION COMPLETE")
    print(f"{'=' * 80}")

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
    print(f"{'=' * 80}")

    return True


def load_cached_sections(cache_path: str) -> Optional[List[Dict]]:
    """Load cached sections from file.

    Args:
        cache_path: Path to cache file

    Returns:
        List of cached section data or None
    """
    if not os.path.exists(cache_path):
        return None

    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load cached sections: {e}")
        return None
