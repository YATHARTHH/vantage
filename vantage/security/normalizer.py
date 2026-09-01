import re
import unicodedata


class TextNormalizer:
    """
    Canonicalizes incoming prompt text before running security rules:
    - Normalizes Unicode characters (NFKD decomposition)
    - Lowercases text
    - Collapses excessive whitespace
    - Reduces extreme character repetition (e.g. 'iiggnnoorree' or 'aaaaa')
    """
    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ""
        # 1. Unicode decomposition (NFKD)
        normalized = unicodedata.normalize("NFKD", text)
        # 2. Lowercase
        normalized = normalized.lower()
        # 3. Collapse whitespace
        normalized = re.sub(r"\s+", " ", normalized)
        # 4. Collapse character repeats > 3 times (e.g., "iiiiiignore" -> "iiignore")
        normalized = re.sub(r"(.)\1{3,}", r"\1\1\1", normalized)
        return normalized.strip()
