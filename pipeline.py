import json
import logging
from google import genai
from google.genai import types
from pydantic import ValidationError
from pydantic_settings import BaseSettings
from schemas import ExtractedInvoice

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    gemini_model: str = "gemini-3.5-flash-lite"
    max_retries: int = 2

settings = Settings()

class ExtractionFailedError(Exception):
    """Raised when the LLM still can't produce a valid invoice after all retries."""

SYSTEM_PROMPT = f"""You are a precise data-extraction engine.
Extract the invoice in the user's text into a single JSON object that follows
this JSON schema exactly:

{json.dumps(ExtractedInvoice.model_json_schema(), indent=2)}

Rules:
- Output ONLY the JSON object, no commentary and no markdown fences.
- Dates must be ISO format (YYYY-MM-DD).
- Monetary values must be plain JSON numbers (no currency symbols or commas).
- The text may be messy OCR output; infer the structure carefully.
- Copy numbers exactly as written in the document; never invent values.
"""
def _text_turn(role: str, text: str) -> types.Content:
    return types.Content(role=role, parts=[types.Part.from_text(text=text)])

def format_validation_error(exc: ValidationError) -> str:
    lines = []
    for err in exc.errors():
        location = ".".join(str(part) for part in err["loc"]) or "invoice"
        lines.append(f"- {location}: {err['msg']}")
    return "\n".join(lines)

def extract_data(raw_text: str, max_retries: int | None = None) -> ExtractedInvoice:
    if max_retries is None:
        max_retries = settings.max_retries

    client = genai.Client()
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
    )

    contents = [_text_turn("user", raw_text)]

    total_attempts = max_retries + 1
    for attempt in range(1, total_attempts + 1):
        logger.info("Gemini extraction attempt %d/%d", attempt, total_attempts)

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=config,
        )
        llm_output = response.text or ""

        try:
            invoice = ExtractedInvoice.model_validate_json(llm_output)
            logger.info("Validation passed on attempt %d", attempt)
            return invoice

        except ValidationError as exc:
            error_text = format_validation_error(exc)
            logger.warning("Validation failed on attempt %d:\n%s", attempt, error_text)

            if attempt == total_attempts:
                raise ExtractionFailedError(
                    f"Could not get a valid invoice after {total_attempts} attempts. "
                    f"Last errors:\n{error_text}"
                ) from exc

            candidates = response.candidates or []
            if candidates and candidates[0].content is not None:
                contents.append(candidates[0].content)
            else:
                contents.append(_text_turn("model", llm_output or "(empty response)"))
            contents.append(
                _text_turn(
                    "user",
                    "Your previous output failed validation:\n"
                    f"{error_text}\n\n"
                    "Fix the math and any other errors, then return the full "
                    "corrected JSON object only.",
                )
            )

    raise ExtractionFailedError("Extraction loop ended unexpectedly.")
