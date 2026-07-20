"""LLMProvider: the interface between agents and whichever model serves them.

Agents depend on this Protocol, never on a concrete SDK. Swapping Gemini
for Claude (or a local model) means writing one new class with this shape
and changing nothing in any agent — the same adapter idea used for
government data sources, applied to the model.
"""

from pathlib import Path
from typing import Protocol


class LLMProvider(Protocol):
    """Anything that can turn a prompt plus PDFs into a text response.

    Implementations are expected to return the model's raw text output
    (which agents then parse and validate). They must not swallow errors:
    network failures and API errors should propagate, per the fail-loudly
    principle.
    """

    def generate(self, prompt: str, pdf_paths: list[Path]) -> str:
        """Send the prompt and the given PDF files to the model.

        Args:
            prompt: Full instruction text for the model.
            pdf_paths: PDF files the model should read alongside the prompt.

        Returns:
            The model's raw text response, expected (but not guaranteed)
            to be JSON — validation is the caller's job.
        """
        ...
