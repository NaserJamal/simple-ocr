import base64
import io
from utils.models import get_model_api_info
from fastapi import HTTPException
from typing import Dict, List
import logging
import asyncio
import pymupdf
from openai import OpenAI
import os
from PIL import Image

log = logging.getLogger(__name__)

MIN_FIELD_SIZE_PT = 5.0  # Minimum field width/height in PDF points
DEFAULT_FIELD_WIDTH = 90.0  # Default width for fields with bad coordinates
DEFAULT_FIELD_HEIGHT = 20.0  # Default height for fields with bad coordinates

async def get_openai_client() -> OpenAI:
    """Initialize OpenAI client with API key from oi-chat"""
    try:
        base_url, api_key, model_id = await get_model_api_info()
        
        if not base_url or not api_key:
            raise HTTPException(
                status_code=500, 
                detail=f"Could not get configuration for model from oi-chat"
            )
        
        return OpenAI(base_url=base_url, api_key=api_key), model_id
        
    except Exception as e:
        log.error(f"Failed to get OpenAI client: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to initialize OpenAI client: {str(e)}"
        )

async def analyze_page_with_llm(page, page_num: int, client: OpenAI, model_id: str, system_prompt: str) -> List[Dict]:
    """
    Analyze a single PDF page with the LLM
    """
    try:
        page_width = float(page.rect.width)
        page_height = float(page.rect.height)

        # Render page to image at 1x resolution (72 DPI)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1, 1), colorspace=pymupdf.csRGB, alpha=False)
        img_width = float(pix.width)
        img_height = float(pix.height)

        # Rescale image to minimize preprocessing by VLM, inorder to increase accuracy
        TARGET_SIZE = 1001 #Trivial number that works with qwen
        img_png_bytes = pix.tobytes("png")
        pil_img = Image.open(io.BytesIO(img_png_bytes)).convert("RGB")

        max_edge = max(pil_img.width, pil_img.height)
        scale = TARGET_SIZE / max_edge if max_edge > 0 else 1.0
        resized_w = int(round(pil_img.width * scale))
        resized_h = int(round(pil_img.height * scale))

        resized_img = pil_img.resize((resized_w, resized_h), Image.LANCZOS)
        canvas = Image.new("RGB", (TARGET_SIZE, TARGET_SIZE), (255, 255, 255))
        canvas.paste(resized_img, (0, 0))

        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        

        user_prompt = (
            f"Please analyze this PDF form image (page {page_num + 1}) and extract all form fields with their coordinates according to the specifications. "
            f"The image width is {TARGET_SIZE} pixels and the image height is {TARGET_SIZE} pixels. "
            "Return rectangles in IMAGE PIXELS with origin at the top-left as [x0, y0, x1, y1]. "
            "Ensure x0 < x1 and y0 < y1 and keep values within the image bounds. Return ONLY the JSON list."
        )

        # Make API call to OpenAI
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=16000,
            temperature=0.1
        )

        response_text = response.choices[0].message.content or ""
        log.info(f"OpenAI response for page {page_num}: {response_text}")

        try:
            import json

            cleaned = response_text.strip()

            # Strip markdown code fences if present
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[: -3]
                cleaned = cleaned.strip()
            else:
                if "```" in cleaned:
                    parts = cleaned.split("```")
                    if len(parts) >= 3:
                        inner = parts[1]
                        if "\n" in inner:
                            cleaned = inner.split("\n", 1)[1].strip()
                        else:
                            cleaned = inner.strip()

            # Extract the first JSON array from the text
            if not (cleaned.startswith("[") and cleaned.endswith("]")):
                start = cleaned.find("[")
                end = cleaned.rfind("]")
                if start != -1 and end != -1 and end > start:
                    cleaned = cleaned[start : end + 1]

            parsed_fields = json.loads(cleaned)

            if isinstance(parsed_fields, list):
                # Convert pixel rectangles to PDF coordinate space (points)
                # Scale factors: pixels → PDF points
                sx = page_width / img_width if img_width else 1.0
                sy = page_height / img_height if img_height else 1.0
                # Undo normalization (padding is at right/bottom; image placed at top-left)
                back_scale_x = (img_width / float(resized_w)) if resized_w else 1.0
                back_scale_y = (img_height / float(resized_h)) if resized_h else 1.0

                transformed_fields: List[Dict] = []
                for field in parsed_fields:
                    try:
                        rect = field.get('rect')
                        if not rect or len(rect) != 4:
                            continue
                        x0_n, y0_n, x1_n, y1_n = [float(v) for v in rect]

                        # Map from normalized/padded space back to original pixel space
                        x0 = x0_n * back_scale_x
                        y0 = y0_n * back_scale_y
                        x1 = x1_n * back_scale_x
                        y1 = y1_n * back_scale_y

                        # Ensure correct ordering of pixel coordinates
                        # VLM returns [x0, y0, x1, y1] in image space (top-left origin)
                        x_left, x_right = sorted([x0, x1])
                        y_top, y_bottom = sorted([y0, y1])

                        # Scale pixel coordinates to PDF points
                        # At 1:1 scale, pixels map directly to PDF annotation coordinates
                        # Both use top-left origin, so no Y-axis flipping is needed
                        pdf_x0 = x_left * sx
                        pdf_x1 = x_right * sx
                        pdf_y0 = y_top * sy
                        pdf_y1 = y_bottom * sy

                        # Clamp to page bounds
                        pdf_x0 = max(0.0, min(page_width, pdf_x0))
                        pdf_x1 = max(0.0, min(page_width, pdf_x1))
                        pdf_y0 = max(0.0, min(page_height, pdf_y0))
                        pdf_y1 = max(0.0, min(page_height, pdf_y1))

                        # Verify valid rectangle
                        if pdf_x0 >= pdf_x1 or pdf_y0 >= pdf_y1:
                            log.warning(f"Invalid rect for field '{field.get('field_name')}': [{pdf_x0}, {pdf_y0}, {pdf_x1}, {pdf_y1}] - skipping")
                            continue

                        field_out = dict(field)
                        field_out['rect'] = [pdf_x0, pdf_y0, pdf_x1, pdf_y1]
                        field_out['page'] = page_num
                        transformed_fields.append(field_out)
                    except Exception as e:
                        log.warning(f"Failed to process field coordinates: {e}")
                        continue

                log.info(f"Successfully parsed {len(transformed_fields)} fields from page {page_num}")
                return transformed_fields
            else:
                log.error(f"Response is not a list for page {page_num}")
                return []

        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON for page {page_num}: {e}")
            return []
        except Exception as e:
            log.error(f"Failed to parse response for page {page_num}: {e}")
            return []

    except Exception as e:
        log.error(f"Failed to analyze page {page_num} with VLM: {e}")
        return []


async def analyze_pdf_fields_with_llm(pdf_path: str) -> List[Dict]:
    """
    Use OpenAI to analyze PDF and identify form fields across all pages concurrently
    """
    try:
        pdf_doc = pymupdf.open(pdf_path)
        num_pages = len(pdf_doc)

        log.info(f"Analyzing {num_pages} pages from PDF")

        # Get client and system prompt once
        client, model_id = await get_openai_client()

        prompt_file_path = os.path.join(os.path.dirname(__file__), 'field_detection_prompt.txt')
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            system_prompt = f.read().strip()

        # Create concurrent tasks for all pages
        tasks = []
        for page_num in range(num_pages):
            page = pdf_doc[page_num]
            task = analyze_page_with_llm(page, page_num, client, model_id, system_prompt)
            tasks.append(task)

        # Wait for all pages to be analyzed concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        pdf_doc.close()

        # Combine all fields from all pages
        all_fields = []
        for page_num, result in enumerate(results):
            if isinstance(result, Exception):
                log.error(f"Error analyzing page {page_num}: {result}")
                continue
            if isinstance(result, list):
                all_fields.extend(result)

        log.info(f"Successfully analyzed {num_pages} pages, found {len(all_fields)} total fields")
        return all_fields

    except Exception as e:
        log.error(f"Failed to analyze PDF with VLM: {e}")
        return []

def validate_and_adjust_rect(rect: List[float], page_width: float, page_height: float, min_dimension: float):
    """
    Force rectangle to be valid within page bounds. Never returns None - always places field on page.
    Coordinates are assumed in PDF space (origin bottom-left).
    """
    try:
        fx0, fy0, fx1, fy1 = [float(v) for v in rect]
    except (TypeError, ValueError):
        # Invalid values - place field at top-left with minimum size
        return (0.0, page_height - min_dimension, min_dimension, page_height)

    # Ensure ordering
    x_min, x_max = sorted([fx0, fx1])
    y_min, y_max = sorted([fy0, fy1])

    # If completely outside page, move to nearest edge
    if x_max <= 0:
        x_min, x_max = 0.0, min_dimension
    elif x_min >= page_width:
        x_max = page_width
        x_min = page_width - min_dimension

    if y_max <= 0:
        y_min, y_max = 0.0, min_dimension
    elif y_min >= page_height:
        y_max = page_height
        y_min = page_height - min_dimension

    # Clamp to page bounds
    x_min = max(0.0, min(x_min, page_width - min_dimension))
    x_max = max(min_dimension, min(x_max, page_width))
    y_min = max(0.0, min(y_min, page_height - min_dimension))
    y_max = max(min_dimension, min(y_max, page_height))

    # Ensure minimum width
    if x_max - x_min < min_dimension:
        if x_min + min_dimension <= page_width:
            x_max = x_min + min_dimension
        else:
            x_max = page_width
            x_min = page_width - min_dimension

    # Ensure minimum height
    if y_max - y_min < min_dimension:
        if y_min + min_dimension <= page_height:
            y_max = y_min + min_dimension
        else:
            y_max = page_height
            y_min = page_height - min_dimension

    return (x_min, y_min, x_max, y_max)

def add_fields_to_pdf(pdf_path: str, fields: List[Dict]) -> str:
    """Add form fields to PDF using PyMuPDF and return path to modified PDF"""
    pdf_doc = pymupdf.open(pdf_path)
    try:
        # Remove all existing form fields from all pages
        for page in pdf_doc:
            widgets = page.widgets()
            for widget in widgets:
                page.delete_widget(widget)

        log.info("Removed all existing form fields from PDF")

        field_type_map = {
            0: pymupdf.PDF_WIDGET_TYPE_TEXT,
            1: pymupdf.PDF_WIDGET_TYPE_CHECKBOX,
            2: pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON,
            3: pymupdf.PDF_WIDGET_TYPE_COMBOBOX,
            4: pymupdf.PDF_WIDGET_TYPE_LISTBOX,
            5: pymupdf.PDF_WIDGET_TYPE_SIGNATURE
        }

        # Grid placement for fields with bad coordinates
        grid_x = 50.0  # Start 50pt from left edge
        grid_y_start = 50.0  # Start 50pt from top
        grid_spacing = 5.0  # Space between fields
        fields_per_row = 5
        grid_col = 0
        grid_row = 0

        added_count = 0
        for idx, field in enumerate(fields):
            # Validate required fields
            rect = field.get('rect')
            if not rect or len(rect) != 4:
                log.warning(f"Skipping field {idx}: invalid rect")
                continue

            page_num = int(field.get('page', 0))
            if page_num < 0 or page_num >= len(pdf_doc):
                log.warning(f"Skipping field {idx}: invalid page {page_num}")
                continue

            page = pdf_doc[page_num]

            # Check if field has reasonable coordinates
            try:
                x0, y0, x1, y1 = [float(v) for v in rect]
                width = abs(x1 - x0)
                height = abs(y1 - y0)
                in_bounds = (0 <= x0 < page.rect.width and 0 <= x1 <= page.rect.width and
                           0 <= y0 < page.rect.height and 0 <= y1 <= page.rect.height)
                has_size = width > 10 and height > 10
                use_original_coords = in_bounds and has_size
            except (TypeError, ValueError):
                use_original_coords = False

            if use_original_coords:
                # Use LLM-provided coordinates (already in PDF space)
                x_min, y_min, x_max, y_max = validate_and_adjust_rect(rect, page.rect.width, page.rect.height, MIN_FIELD_SIZE_PT)
            else:
                # Place in grid - LLM gave bad coordinates
                x_min = grid_x + (grid_col * (DEFAULT_FIELD_WIDTH + grid_spacing))
                y_min = page.rect.height - grid_y_start - (grid_row * (DEFAULT_FIELD_HEIGHT + grid_spacing)) - DEFAULT_FIELD_HEIGHT
                x_max = x_min + DEFAULT_FIELD_WIDTH
                y_max = y_min + DEFAULT_FIELD_HEIGHT
                log.info(f"Field '{field.get('field_name')}' placed in grid at position (row={grid_row}, col={grid_col})")

                # Advance grid position
                grid_col += 1
                if grid_col >= fields_per_row:
                    grid_col = 0
                    grid_row += 1

            # Convert numeric field type to PyMuPDF constant, default to text
            field_type = field.get('field_type')
            if isinstance(field_type, int):
                field_type = field_type_map.get(field_type, pymupdf.PDF_WIDGET_TYPE_TEXT)

            # Create and add widget
            try:
                widget = pymupdf.Widget()
                widget.field_name = field.get('field_name', f"field_{idx}")
                widget.field_label = field.get('field_label', widget.field_name)
                widget.field_type = field_type
                widget.rect = pymupdf.Rect(x_min, y_min, x_max, y_max)
                widget.xref = int(field.get('xref', 0))
                page.add_widget(widget)
                added_count += 1
            except Exception as e:
                log.warning(f"Failed to add field {idx}: {e}")
                continue

        # Save the modified PDF
        output_path = pdf_path.replace('.pdf', '_with_fields.pdf')
        pdf_doc.save(output_path)
        log.info(f"Added {added_count}/{len(fields)} fields to PDF")
        return output_path

    except Exception as e:
        log.error(f"Error adding fields to PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add fields to PDF: {str(e)}")
    finally:
        pdf_doc.close()
