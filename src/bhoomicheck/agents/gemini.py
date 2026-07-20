"""GeminiProvider: LLMProvider implementation backed by Google's Gemini API.

Deliberately thin — file reading, one SDK call, return text. All parsing,
validation, and retry logic lives in the agent, where it is tested against
a fake provider. Swapping this class out never touches agent code.
"""

from pathlib import Path

from google import genai
from google.genai import types


class GeminiProvider:
    """Satisfies the LLMProvider Protocol using the Gemini API.

    Requires GEMINI_API_KEY in the environment; genai.Client() reads it
    automatically, so no key ever appears in code or configuration files
    that could be committed.
    """

    def __init__(self, model: str = "gemini-3.5-flash") -> None:
        """
        Args:
            model: Gemini model name. Flash is the free-tier workhorse;
                configurable so a quality comparison later is a one-line
                change at the call site.
        """
        self.model = model
        self.client = genai.Client()

    def generate(self, prompt: str, pdf_paths: list[Path]) -> str:
        """Send the prompt and PDFs to Gemini, return its raw text response."""
        parts: list[types.Part | str] = [
            types.Part.from_bytes(
                data=path.read_bytes(), mime_type="application/pdf"
            )
            for path in pdf_paths
        ]
        parts.append(prompt)
        response = self.client.models.generate_content(
            model=self.model,
            contents=parts,
            # Constrain output to bare JSON: without this, models often wrap
            # valid JSON in markdown fences, which would burn our validation
            # retries on formatting noise instead of real schema errors.
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )
        # .text is None if the model returned no usable candidates (e.g.
        # safety-blocked). Fail loudly rather than hand "" to the validator.
        if response.text is None:
            raise RuntimeError(
                f"Gemini returned no text (prompt_feedback: {response.prompt_feedback})"
            )
        return response.text
