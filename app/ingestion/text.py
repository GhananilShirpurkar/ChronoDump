"""Text ingestion handler."""

import re


class TextIngestion:
    """Sanitizes and normalizes plain text dumps."""

    @staticmethod
    def clean_text(raw_text: str) -> str:
        """Strip control chars and collapse redundant whitespace."""
        text = raw_text.strip()
        text = re.sub(r"[ \t]+", " ", text)
        return text
