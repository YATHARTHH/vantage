import base64
import re
import urllib.parse


class PayloadDecoder:
    """
    Safely inspects candidate encoded strings (Base64, URL encoding, Unicode escapes):
    - Strict safety caps: max_decoded_bytes = 4096, max_nesting_depth = 2
    - Prevents CPU/Memory Denial-of-Service attacks.
    """
    MAX_DECODED_BYTES = 4096
    MAX_NESTING_DEPTH = 2

    @classmethod
    def decode_candidates(cls, text: str, current_depth: int = 0) -> list[str]:
        if not text or current_depth >= cls.MAX_NESTING_DEPTH:
            return []

        decoded_results: list[str] = []

        # 1. URL decoding
        if "%" in text:
            try:
                unquoted = urllib.parse.unquote(text)
                if unquoted != text and len(unquoted.encode("utf-8")) <= cls.MAX_DECODED_BYTES:
                    decoded_results.append(unquoted)
            except Exception:
                pass

        # 2. Base64 payload detection (regex for Base64 blocks > 16 chars)
        b64_pattern = r"(?:[A-Za-z0-9+/]{4}){4,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?"
        for match in re.finditer(b64_pattern, text):
            candidate = match.group(0)
            try:
                raw_bytes = base64.b64decode(candidate, validate=True)
                if len(raw_bytes) <= cls.MAX_DECODED_BYTES:
                    decoded_str = raw_bytes.decode("utf-8", errors="ignore")
                    if len(decoded_str.strip()) > 5:
                        decoded_results.append(decoded_str)
                        # Recursive check for nested encodings up to MAX_NESTING_DEPTH
                        nested = cls.decode_candidates(decoded_str, current_depth + 1)
                        decoded_results.extend(nested)
            except Exception:
                continue

        return decoded_results
