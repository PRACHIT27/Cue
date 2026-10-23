from __future__ import annotations

import re
from typing import Mapping

PLACEHOLDER = re.compile(r"\{\{([^{}]+)\}\}")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
TITLE = re.compile(r"\*([^*\n]{2,80})\*|\"([^\"\n]{2,80})\"|“([^”\n]{2,80})”")


def sentences(text: str) -> list[str]:
    parts: list[str] = []
    for paragraph in text.split("\n"):
        parts.extend(s for s in SENTENCE_END.split(paragraph) if s.strip())
        parts.append("\n")
    return parts[:-1] if parts else []


def join_sentences(parts: list[str]) -> str:
    text = ""
    for part in parts:
        if part == "\n":
            text = text.rstrip(" ") + "\n"
        else:
            text += ("" if not text or text.endswith("\n") else " ") + part.strip()
    return text.strip()


def placeholder_ids(text: str) -> list[str]:
    return [match.strip() for match in PLACEHOLDER.findall(text)]


def fill_placeholders(text: str, names: Mapping[str, str]) -> str:
    return PLACEHOLDER.sub(lambda m: names.get(m.group(1).strip(), m.group(0)), text)


def quoted_titles(text: str) -> list[str]:
    return [next(group for group in match if group).strip() for match in TITLE.findall(text)]
