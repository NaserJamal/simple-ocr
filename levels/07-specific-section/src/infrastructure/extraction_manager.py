"""Manages extraction results, indexing, and file operations."""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


class ExtractionManager:
    """Handles saving, loading, and indexing extraction results."""

    def __init__(self, output_dir: str, extraction_id: str, timestamp: str):
        """Initialize extraction manager.

        Args:
            output_dir: Base output directory
            extraction_id: UUID for this extraction
            timestamp: ISO timestamp for this extraction
        """
        self.output_dir = output_dir
        self.extraction_id = extraction_id
        self.timestamp = timestamp

        # Create extraction-specific subdirectory
        self.extraction_dir = os.path.join(
            output_dir,
            f"extraction_{extraction_id[:8]}_{datetime.fromisoformat(timestamp).strftime('%Y%m%d_%H%M%S')}"
        )
        os.makedirs(self.extraction_dir, exist_ok=True)

    def save_json_results(self, results: List[Dict]) -> None:
        """Save results to JSON file in extraction directory."""
        output_path = os.path.join(self.extraction_dir, "sections.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        log.info(f"Saved JSON results to {output_path}")

    def save_text_results(self, text_parts: List[str]) -> None:
        """Save extracted text to .txt file in extraction directory."""
        output_path = os.path.join(self.extraction_dir, "extracted_text.txt")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(text_parts))
        log.info(f"Saved extracted text to {output_path}")

    def update_extraction_index(self, results: List[Dict], pdf_path: str, section_request: Optional[str]) -> None:
        """Update the extraction index with metadata about this extraction."""
        index_path = os.path.join(self.output_dir, "extraction_index.json")

        # Load existing index or create new
        index = self._load_index()

        # Add current extraction metadata
        summary = self._generate_summary(results)
        index.append({
            "extraction_id": self.extraction_id,
            "timestamp": self.timestamp,
            "extraction_dir": os.path.basename(self.extraction_dir),
            "pdf_path": pdf_path,
            "section_request": section_request,
            "summary": summary
        })

        # Save updated index
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        log.info(f"Updated extraction index: {index_path}")

    def _load_index(self) -> List[Dict]:
        """Load extraction index."""
        index_path = os.path.join(self.output_dir, "extraction_index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                log.warning(f"Failed to load extraction index: {e}")
        return []

    @staticmethod
    def load_latest_cached_sections(output_dir: str) -> Optional[List[Dict]]:
        """Load sections from the most recent extraction.

        Args:
            output_dir: Base output directory

        Returns:
            List of section data from latest extraction, or None if not found
        """
        index_path = os.path.join(output_dir, "extraction_index.json")
        if not os.path.exists(index_path):
            return None

        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
                if not index:
                    return None

                # Get most recent extraction
                latest = index[-1]
                extraction_dir = os.path.join(output_dir, latest['extraction_dir'])
                sections_path = os.path.join(extraction_dir, 'sections.json')

                if os.path.exists(sections_path):
                    with open(sections_path, 'r', encoding='utf-8') as sf:
                        return json.load(sf)
        except Exception as e:
            log.warning(f"Failed to load cached sections: {e}")
        return None

    @staticmethod
    def _generate_summary(results: List[Dict]) -> Dict:
        """Generate summary statistics from extraction results."""
        section_types: Dict[str, int] = {}
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
            "total_characters_extracted": total_chars,
        }
