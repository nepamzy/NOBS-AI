"""Heuristic policy-risk scan every script goes through before any paid
voice/video generation runs (a new COMPLIANCE_CHECK pipeline stage, between
STORYBOARD_REVIEW and VOICE).

Important honesty note, worth keeping in mind while reading this file: this
is a keyword/pattern scanner, not a YouTube-policy classifier. It cannot
know what YouTube's own enforcement systems will actually decide — only
YouTube does. Its job is to catch the small number of things that ARE
reliably detectable this way (near-duplicate uploads, a short list of
unambiguous red-flag phrases) and to surface everything else as a
*warning* for Nobert's own judgment, never a false sense of certainty.

Deliberately BLOCKS only near-duplicate content (the one check this can do
reliably and that YouTube's own "reused/repetitious content" policy names
directly) — sensitive-topic language is a WARNING, not a block, since a
storytelling channel legitimately narrates dramatic/difficult topics and a
keyword match can't tell a gratuitous mention from a sensitive, well-told
one. That judgment call stays with Nobert.
"""

import re
from dataclasses import dataclass, field

DUPLICATE_TITLE_OVERLAP_THRESHOLD = 0.85  # fraction of shared words to flag as near-duplicate

# Short, deliberately narrow phrase lists — false negatives are far
# preferable to false positives here, since a block requires a human fix
# and a miss is caught by YouTube's own review either way.
_SENSITIVE_PATTERNS: dict[str, list[str]] = {
    "self-harm or suicide": [r"\bsuicide\b", r"\bself[- ]harm\b", r"\bkill(ing)? myself\b"],
    "dangerous acts": [
        r"\bhow to make a bomb\b",
        r"\bchoking challenge\b",
        r"\bdo this challenge at home\b",
    ],
    "medical misinformation": [
        r"\bcures? cancer\b",
        r"\bmiracle cure\b",
        r"\bcures? covid\b",
    ],
    "financial misinformation": [
        r"\bguaranteed returns?\b",
        r"\bguaranteed profit\b",
        r"\bget rich quick\b",
    ],
}


@dataclass
class ComplianceResult:
    passed: bool
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _normalize_words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", text.lower()))


def _title_overlap(a: str, b: str) -> float:
    words_a, words_b = _normalize_words(a), _normalize_words(b)
    if not words_a or not words_b:
        return 0.0
    shared = words_a & words_b
    return len(shared) / min(len(words_a), len(words_b))


def check_script(
    title: str,
    hook: str,
    scene_narrations: list[str],
    previous_titles: list[str],
) -> ComplianceResult:
    blockers: list[str] = []
    warnings: list[str] = []

    for previous_title in previous_titles:
        overlap = _title_overlap(title, previous_title)
        if overlap >= DUPLICATE_TITLE_OVERLAP_THRESHOLD:
            blockers.append(
                f"Title is {overlap:.0%} similar to a previous video's title "
                f'("{previous_title}") — YouTube\'s reused/repetitious content '
                "policy targets exactly this pattern. Change the angle or title "
                "before continuing."
            )

    full_text = " ".join([title, hook, *scene_narrations])
    for category, patterns in _SENSITIVE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                warnings.append(
                    f"Script contains language matching '{category}' — not "
                    "blocked (storytelling often covers hard topics well), "
                    "but worth a look before this goes out."
                )
                break  # one warning per category is enough

    warnings.append(
        "Reminder: if this video meaningfully alters reality or uses "
        "realistic AI voice, enable YouTube Studio's 'Altered or Synthetic "
        "Content' disclosure toggle before publishing."
    )

    return ComplianceResult(passed=not blockers, blockers=blockers, warnings=warnings)
