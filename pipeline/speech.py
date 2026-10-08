"""Turn caption narration into text a speech voice reads naturally.

Driven by the template's `speech:` block. `narration` (captions, transcript)
is left as written; this produces a separate `speech` string for TTS.
"""

from __future__ import annotations

import re
from typing import Any

_DIGIT_WORDS = ["oh", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
# A leading 0 then digits and spaces, not touching other digits, letters or hyphens
# (so "FBS-2026-104381" and "2026" don't match). Digit count is checked separately.
_PHONE = re.compile(r"(?<![\w-])0[\d ]{8,12}\d(?![\w-])")


def to_speech(text: str, rules: dict[str, Any]) -> str:
    """Apply each speech rule in turn. Unknown rules are an error, not ignored."""
    for rule, setting in rules.items():
        if rule == "phone_numbers":
            if setting != "digits":
                raise ValueError(f"Unsupported speech rule phone_numbers: {setting!r}")
            text = _PHONE.sub(_speak_phone, text)
        elif rule == "symbols":
            for symbol, spoken in setting.items():
                text = text.replace(symbol, spoken)
        else:
            raise ValueError(f"Unknown speech rule {rule!r}")
    return " ".join(text.split())


def _speak_phone(match: re.Match[str]) -> str:
    """'01632 960412' -> 'oh one six three two, nine six oh, four one two'.

    Commas between groups make TTS voices pause, as a person would.
    """
    written = match.group(0)
    digits = written.replace(" ", "")
    if not 10 <= len(digits) <= 11:  # UK numbers; anything else is left alone
        return written

    groups = written.split() if " " in written else [digits[:5], digits[5:]]
    spoken_groups = [groups[0]]
    for group in groups[1:]:
        # Long groups are read in threes: "960412" -> "960", "412".
        while len(group) > 4:
            spoken_groups.append(group[:3])
            group = group[3:]
        spoken_groups.append(group)
    return ", ".join(" ".join(_DIGIT_WORDS[int(d)] for d in group) for group in spoken_groups)
