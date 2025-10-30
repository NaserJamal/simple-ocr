"""
Template-based extraction module using Vision Language Models
"""
import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

from .image_processor import ImageProcessor
from .config import API_TEMPERATURE

load_dotenv("../../.env")

TEMPLATES = {
    "eid": {
        "name": "UAE Emirates ID",
        "prompt_file": "templates/uae_emirates_id.txt"
    },
    "passport": {
        "name": "UAE Passports",
        "prompt_file": "templates/passport.txt"
    }
}


class TemplateExtractor:
    """Handles template-based document extraction using VLMs."""

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OCR_MODEL_API_KEY"),
            base_url=os.getenv("OCR_MODEL_BASE_URL")
        )
        self.processor = ImageProcessor()

    def load_template_prompt(self, template_key: str) -> str:
        """Load the system prompt for a given template."""
        if template_key not in TEMPLATES:
            raise ValueError(f"Template '{template_key}' not found")

        prompt_path = Path(__file__).parent.parent / TEMPLATES[template_key]["prompt_file"]
        return prompt_path.read_text(encoding='utf-8')

    def select_template(self) -> str:
        """Prompt user to select a template."""
        print("\nAvailable Templates:")
        print("-" * 40)

        template_list = list(TEMPLATES.items())
        for idx, (key, info) in enumerate(template_list, 1):
            print(f"{idx}. [{key}] {info['name']}")

        print("-" * 40)

        while True:
            choice = input("\nSelect a template (enter number or key): ").strip()

            # Try selection by number
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(template_list):
                    return template_list[idx][0]

            # Try selection by key
            if choice in TEMPLATES:
                return choice

            print(f"Invalid selection. Please choose 1-{len(template_list)} or a valid key.")

    def extract(self, file_path: str, template_key: str) -> str:
        """Extract structured data from an image/PDF using VLM."""
        system_prompt = self.load_template_prompt(template_key)

        print(f"\nProcessing document with template: {TEMPLATES[template_key]['name']}...")
        img_b64 = self.processor.process_file(file_path)

        response = self.client.chat.completions.create(
            model=os.getenv("OCR_MODEL_NAME"),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": system_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                ]
            }],
            temperature=API_TEMPERATURE,
            response_format={"type": "json_object"}
        )

        return response.choices[0].message.content

    def save_output(self, data: str, output_path: Path) -> None:
        """Save extracted data to a JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            json_data = json.loads(data)
            output_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"\nExtracted data saved to: {output_path}")
            print("\nExtracted Data:")
            print(json.dumps(json_data, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            output_path.write_text(data, encoding='utf-8')
            print(f"\nResponse saved to: {output_path}")
            print("\nWarning: Response is not valid JSON")
