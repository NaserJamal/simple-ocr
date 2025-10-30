"""
Template-Based Document Parser
Extracts structured data from documents using Vision Language Models
"""
from pathlib import Path
from utils.extractor import TemplateExtractor, TEMPLATES


def main() -> None:
    """Main execution flow."""
    print("=" * 40)
    print("Template-Based Document Parser")
    print("=" * 40)

    extractor = TemplateExtractor()

    template_key = extractor.select_template()
    print(f"\nSelected: {TEMPLATES[template_key]['name']}")

    file_path = input("\nEnter the path to the image/document (PDF, PNG, JPG): ").strip()

    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        return

    try:
        result = extractor.extract(file_path, template_key)
        output_path = Path(__file__).parent / "output" / f"extracted_{template_key}.json"
        extractor.save_output(result, output_path)
    except Exception as e:
        print(f"\nError during extraction: {e}")
        raise


if __name__ == "__main__":
    main()
