"""pieceofmind.checkers -- label-free structural checkers for prompt-section attribution.

The main adoption barrier for attributing a prompt's pass-rate to its sections is that most people
have NO labeled eval set. These checkers need NO ground truth -- they assert the STRUCTURE of the
output (valid JSON, required keys, length, no refusal/preamble). That lets you point pieceofmind at
your existing system prompt / CLAUDE.md / Cursor-rules with zero labeling: which sections keep the
output valid JSON, which are dead weight, which are harmful?

Each checker is ``(output, input=None) -> bool``. Compose with ``all_of`` and build a value function:

    import pieceofmind.checkers as C
    check = C.all_of(C.valid_json, C.has_keys("name", "email"))
    def value_fn(subset_sections):
        sys = "\\n".join(SECTIONS[s] for s in subset_sections)
        return sum(check(llm(sys, t)) for t in TESTS) / len(TESTS)
"""

from __future__ import annotations

import json
import re

_JSON = re.compile(r"\{.*\}|\[.*\]", re.S)


def _extract_json(text: str) -> str:
    m = _JSON.search(text or "")
    return m.group(0) if m else (text or "")


def valid_json(output: str, _input=None) -> bool:
    """True iff the output contains a parseable JSON object/array (markdown fences tolerated)."""
    try:
        json.loads(_extract_json(output))
        return True
    except Exception:
        return False


def has_keys(*keys):
    """Checker: output parses as a JSON object containing ALL of the given keys."""
    def check(output: str, _input=None) -> bool:
        try:
            obj = json.loads(_extract_json(output))
        except Exception:
            return False
        return isinstance(obj, dict) and all(k in obj for k in keys)
    return check


def under_words(n: int):
    """Checker: output has at most n whitespace-separated tokens."""
    return lambda output, _input=None: len((output or "").split()) <= n


_REFUSAL = re.compile(r"\b(?:i\s*(?:'m|am)?\s*(?:sorry|unable|can(?:'?t|not)))\b", re.I)


def no_refusal(output: str, _input=None) -> bool:
    """True iff the output is not a refusal ('I'm sorry', 'I can't', 'unable to')."""
    return not _REFUSAL.search(output or "")


def no_preamble(output: str, _input=None) -> bool:
    """True iff the output starts with structure (JSON/list/number), not conversational prose."""
    s = (output or "").lstrip().lstrip("`").lstrip()
    return bool(s) and s[0] in '{[-0123456789"'


def contains(substring: str, *, ignore_case: bool = True):
    """Checker: output contains the given substring."""
    sub = substring.lower() if ignore_case else substring
    return lambda output, _input=None: sub in ((output or "").lower() if ignore_case else (output or ""))


def all_of(*checks):
    """Compose checkers: passes iff every checker passes."""
    return lambda output, _input=None: all(c(output, _input) for c in checks)
