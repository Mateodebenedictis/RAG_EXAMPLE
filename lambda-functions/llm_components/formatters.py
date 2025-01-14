import json
from typing import Dict, Any


def format_presentation_content(content: str) -> str:
    """Format the presentation content to ensure valid JSON for each slide."""

    slides = content.split("[Slide ")
    formatted_slides = []

    for slide in slides[1:]:
        slide_number, slide_content = slide.split("]", 1)
        try:
            json_content = json.loads(slide_content.strip())
            formatted_json = json.dumps(json_content, indent=2)
            formatted_slide = f"[Slide {slide_number}]\n{formatted_json}"
            formatted_slides.append(formatted_slide)
        except json.JSONDecodeError:
            formatted_slides.append(f"[Slide {slide_number}]{slide_content}")

    return "\n\n".join(formatted_slides)


def extract_metadata(response) -> Dict[str, Any]:
    """Extract metadata from the LLM response."""

    metadata = {
        "model_id": response.response_metadata.get("model_id", "Unknown"),
        "stop_reason": response.response_metadata.get("stop_reason", "Unknown"),
        "token_usage": {
            "prompt_tokens": response.usage_metadata.get("input_tokens", 0),
            "output_tokens": response.usage_metadata.get("output_tokens", 0),
            "total_tokens": response.usage_metadata.get("total_tokens", 0),
        },
    }
    return metadata


def format_layout_documents(docs):
    """Format the layout documents for LLM input."""

    return "\n".join(
        f"""
    <layout id="{doc.metadata.get('id')}" index="{i+1}">
    {doc.page_content}
    </layout>
    """
        for i, doc in enumerate(docs)
    )
