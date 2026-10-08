"""Flesch Reading Ease with a simple syllable heuristic (no dictionary needed).

Score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words).
Higher is easier; 60+ is roughly plain English. The heuristic is within about
one syllable on most words - good enough for a warning threshold.
"""

from __future__ import annotations

import re

_VOWEL_GROUP = re.compile(r"[aeiouy]+")
# A word, a contraction like "don't", or a number like 1,359.76 (one token).
_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+(?:[,.]\d+)*")
# A sentence ends at . ! ? followed by whitespace - so the "." in "1,359.76"
# doesn't split one. Shared with captions so both agree on what a sentence is.
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
_VOWELS = "aeiouy"


def count_syllables(word: str) -> int:
    """Estimate syllables: vowel groups, minus a silent final 'e' or '-ed'."""
    if any(char.isdigit() for char in word):
        # Rough: one per digit. "1,359.76" read aloud is long, so this errs
        # towards a lower (stricter) score.
        return sum(char.isdigit() for char in word)

    letters = re.sub(r"[^a-z]", "", word.lower())
    if not letters:
        return 0
    count = len(_VOWEL_GROUP.findall(letters))

    # "rate" -> 1, but "table" keeps its "-le" syllable after a consonant.
    spoken_le = letters.endswith("le") and len(letters) > 2 and letters[-3] not in _VOWELS
    silent_e = letters.endswith("e") and not spoken_le
    # "explained" -> 2, but "wanted" / "added" keep the "-ed" syllable.
    silent_ed = letters.endswith("ed") and len(letters) > 2 and letters[-3] not in "td"
    if silent_e or silent_ed:
        count -= 1

    return max(1, count)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, keeping each one's closing punctuation."""
    return [sentence for sentence in _SENTENCE_BREAK.split(text.strip()) if sentence]


def flesch_reading_ease(text: str) -> float:
    """Return the Flesch Reading Ease score for `text`, rounded to 1 dp."""
    words = _WORD.findall(text)
    if not words:
        raise ValueError("Can't score text with no words")
    sentences = len(split_sentences(text))
    syllables = sum(count_syllables(word) for word in words)

    score = 206.835 - 1.015 * (len(words) / sentences) - 84.6 * (syllables / len(words))
    return round(score, 1)
