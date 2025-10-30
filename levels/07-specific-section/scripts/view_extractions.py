#!/usr/bin/env python3
"""Utility to view and manage extraction history."""

import json
import os
import sys

from src.infrastructure.config import OUTPUT_DIR


def load_index():
    """Load extraction index."""
    index_path = os.path.join(OUTPUT_DIR, "extraction_index.json")
    if not os.path.exists(index_path):
        print(f"No extraction index found at {index_path}")
        return []

    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def display_extractions():
    """Display all extractions in a formatted table."""
    index = load_index()
    if not index:
        print("No extractions found.")
        return

    print("\n" + "=" * 120)
    print(f"{'#':<4} {'Extraction ID':<12} {'Timestamp':<22} {'Request':<35} {'Sections':<10} {'Pages'}")
    print("=" * 120)

    for i, entry in enumerate(index, 1):
        extraction_id = entry['extraction_id'][:8]
        timestamp = entry['timestamp'][:19].replace('T', ' ')
        request = entry.get('section_request', 'N/A') or 'Full document'
        if len(request) > 35:
            request = request[:32] + '...'

        summary = entry.get('summary', {})
        total_sections = summary.get('total_sections', 0)
        successful_pages = summary.get('successful_pages', 0)

        print(f"{i:<4} {extraction_id:<12} {timestamp:<22} {request:<35} {total_sections:<10} {successful_pages}")

    print("=" * 120)
    print(f"\nTotal extractions: {len(index)}\n")


def view_extraction_details(index_num):
    """View detailed information about a specific extraction."""
    index = load_index()
    if not index or index_num < 1 or index_num > len(index):
        print(f"Invalid extraction number. Please choose between 1 and {len(index)}")
        return

    entry = index[index_num - 1]
    print("\n" + "=" * 80)
    print(f"Extraction Details - #{index_num}")
    print("=" * 80)
    print(f"Extraction ID:    {entry['extraction_id']}")
    print(f"Timestamp:        {entry['timestamp']}")
    print(f"PDF Path:         {entry['pdf_path']}")
    print(f"Section Request:  {entry.get('section_request') or 'Full document'}")
    print(f"Extraction Dir:   {entry['extraction_dir']}")

    summary = entry.get('summary', {})
    print(f"\nSummary:")
    print(f"  Total Sections:     {summary.get('total_sections', 0)}")
    print(f"  Successful Pages:   {summary.get('successful_pages', 0)}")
    print(f"  Failed Pages:       {summary.get('failed_pages', 0)}")
    print(f"  Total Characters:   {summary.get('total_characters_extracted', 0)}")

    section_types = summary.get('section_types', {})
    if section_types:
        print(f"\nSection Types:")
        for section_type, count in section_types.items():
            print(f"    {section_type}: {count}")

    print("=" * 80 + "\n")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        try:
            index_num = int(sys.argv[1])
            view_extraction_details(index_num)
        except ValueError:
            print(f"Usage: {sys.argv[0]} [extraction_number]")
            print(f"Example: {sys.argv[0]} 1  # View details of extraction #1")
    else:
        display_extractions()


if __name__ == "__main__":
    main()
