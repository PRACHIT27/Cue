from __future__ import annotations

import re
import unicodedata


def normalise_name(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    words = text.split()
    if words and words[0] == "the":
        words = words[1:]
    return " ".join(words)


def names_match(a: str, b: str) -> bool:
    return normalise_name(a) == normalise_name(b)
