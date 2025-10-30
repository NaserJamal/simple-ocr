import os
import json
import base64
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv("../../.env")

# Available templates
TEMPLATES = {
    "eid": {
        "name": "UAE Emirates ID",
        "prompt_file": "templates/uae_emirates_id.txt"
    }
}


def load_template_prompt(template_key):
    """Load the system prompt for a given template."""
    template = TEMPLATES.get(template_key)
    if not template:
        raise ValueError(f"Template '{template_key}' not found")

    prompt_path = Path(__file__).parent / template["prompt_file"]
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def select_template():
    """Prompt user to select a template."""
    print("\nAvailable Templates:")
    print("-" * 40)

    template_list = list(TEMPLATES.items())
    for idx, (key, info) in enumerate(template_list, 1):
        print(f"{idx}. [{key}] {info['name']}")

    print("-" * 40)

    while True:
        try:
            choice = input("\nSelect a template (enter number or key): ").strip()

            # Try by number
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(template_list):
                    return template_list[idx][0]

            # Try by key
            if choice in TEMPLATES:
                return choice

            print(f"Invalid selection. Please choose 1-{len(template_list)} or a valid key.")
        except (ValueError, KeyError):
            print("Invalid input. Please try again.")


def image_to_base64(image_path):
    """Convert an image file to base64 string."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode()


def extract_with_vlm(image_path, template_key):
    """Extract structured data from an image using VLM with the specified template."""
    # Initialize OpenAI client
    client = OpenAI(
        api_key=os.getenv("OCR_MODEL_API_KEY"),
        base_url=os.getenv("OCR_MODEL_BASE_URL")
    )

    # Load template prompt
    system_prompt = load_template_prompt(template_key)

    # Convert image to base64
    img_b64 = image_to_base64(image_path)

    # Make API request
    print(f"\nProcessing image with template: {TEMPLATES[template_key]['name']}...")

    response = client.chat.completions.create(
        model=os.getenv("OCR_MODEL_NAME"),
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": system_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
            ]
        }],
        temperature=0  # Use deterministic output for extraction
    )

    return response.choices[0].message.content


def save_output(data, output_path):
    """Save extracted data to a JSON file."""
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Try to parse as JSON for pretty formatting
    try:
        json_data = json.loads(data)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"\nExtracted data saved to: {output_path}")
        print("\nExtracted Data:")
        print(json.dumps(json_data, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        # If not valid JSON, save as-is
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(data)
        print(f"\nResponse saved to: {output_path}")
        print(f"\nWarning: Response is not valid JSON")


def main():
    """Main execution flow."""
    print("=" * 40)
    print("Template-Based Document Parser")
    print("=" * 40)

    # Select template
    template_key = select_template()
    print(f"\nSelected: {TEMPLATES[template_key]['name']}")

    # Get image path
    image_path = input("\nEnter the path to the image/document: ").strip()

    # Validate image path
    if not os.path.exists(image_path):
        print(f"Error: File not found: {image_path}")
        return

    # Extract data
    try:
        result = extract_with_vlm(image_path, template_key)

        # Save output
        output_path = Path(__file__).parent / "output" / f"extracted_{template_key}.json"
        save_output(result, output_path)

    except Exception as e:
        print(f"\nError during extraction: {str(e)}")
        raise


if __name__ == "__main__":
    main()
