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

_DECODER = json.JSONDecoder()


def _extract_json(text: str) -> str:
    """First substring that PARSES as a JSON object/array (fences/surrounding prose tolerated),
    else the original text. Scans '{'/'[' positions with raw_decode instead of a greedy
    ``\\{.*\\}`` regex -- the greedy regex splices two separate objects into an invalid
    superstring (``{a} ... {"k":1}`` -> the whole span), failing valid output that contains
    a real JSON value."""
    t = text or ""
    for i, ch in enumerate(t):
        if ch in "{[":
            try:
                _obj, end = _DECODER.raw_decode(t, i)
                return t[i:end]
            except ValueError:
                continue
    return t


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


# A refusal couples an inability ("I can't/cannot/won't/unable to") with the first person, OR the
# classic "I'm sorry, but ..." opener. Bare "sorry" is NOT a refusal -- "I am sorry to hear that;
# here is the JSON" is a normal (non-refusing) reply and must pass.
_REFUSAL = re.compile(
    r"\bi\s*(?:'m|am)?\s*(?:can(?:'?t|not)|won'?t|will\s+not|unable\s+to|not\s+able\s+to)\b"
    r"|\bi\s*(?:'m|am)\s+sorry,?\s+but\b",
    re.I,
)


def no_refusal(output: str, _input=None) -> bool:
    """True iff the output is not a refusal. Fires on inability phrasing ('I can't', 'I cannot',
    'I'm unable to', 'I won't') and the 'I'm sorry, but ...' opener -- NOT on a bare 'sorry'."""
    return not _REFUSAL.search(output or "")


_OPEN_FENCE = re.compile(r"^\s*```[A-Za-z0-9_+-]*[ \t]*\r?\n?")


def no_preamble(output: str, _input=None) -> bool:
    """True iff the output starts with structure (JSON/list/number), not conversational prose.
    An opening markdown code fence (```json) is stripped first, so fence policy matches
    ``valid_json`` (which also tolerates fences) -- the two no longer disagree about fenced output."""
    s = _OPEN_FENCE.sub("", (output or "").lstrip(), count=1).lstrip()
    return bool(s) and s[0] in '{[-0123456789"'


def contains(substring: str, *, ignore_case: bool = True):
    """Checker: output contains the given substring."""
    sub = substring.lower() if ignore_case else substring
    return lambda output, _input=None: sub in ((output or "").lower() if ignore_case else (output or ""))


def all_of(*checks):
    """Compose checkers: passes iff every checker passes."""
    return lambda output, _input=None: all(c(output, _input) for c in checks)
