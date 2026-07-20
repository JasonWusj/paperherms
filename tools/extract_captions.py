from __future__ import annotations

import re


def extract_captions(text: str) -> list[str]:
    pattern = re.compile(r"(?im)^\s*(?:Figure|Fig\.|Table)\s+\d+[:.]\s+.+$")
    return [match.group(0).strip() for match in pattern.finditer(text)]
