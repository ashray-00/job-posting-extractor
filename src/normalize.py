from __future__ import annotations

import re
import unicodedata


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

_ZWSP = re.compile(r"[\u200b\u200c\u200d\ufeff\u00a0]")
_MULTI_WS = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = _ZWSP.sub(" ", s)
    s = s.lower().strip()
    s = _MULTI_WS.sub(" ", s)
    return s


# ---------------------------------------------------------------------------
# Money parsing
# ---------------------------------------------------------------------------

_CURRENCY_CHARS = re.compile(r"[€$£]|EUR|USD|GBP", re.IGNORECASE)
_MONEY_PAT = re.compile(
    r"""
    (?<![a-zA-Z])            # not preceded by a letter
    (\d{1,3}(?:[.\s,]\d{3})* # grouped thousands  e.g. 65.000 / 65,000 / 65 000
     |\d+)                   # or plain digits
    \s*[kK]?                 # optional k/K suffix
    (?![a-zA-Z])             # not followed by a letter (other than k already consumed)
    """,
    re.VERBOSE,
)


def parse_money(s: str) -> int | None:
    cleaned = _CURRENCY_CHARS.sub("", s).strip()
    m = _MONEY_PAT.search(cleaned)
    if m is None:
        return None
    token = m.group(0).strip()
    has_k = token[-1] in ("k", "K")
    if has_k:
        token = token[:-1].strip()
    digits = re.sub(r"[\s.,]", "", token)
    if not digits.isdigit():
        return None
    value = int(digits)
    if has_k:
        value *= 1000
    return value


# ---------------------------------------------------------------------------
# Skill normalization
# ---------------------------------------------------------------------------

_STRIP_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_VERSION_SUFFIX = re.compile(r"[\d.]+$")
_JS_SUFFIX = re.compile(r"js$", re.IGNORECASE)


def normalize_skill(s: str, vocab: dict[str, str] | None = None) -> str:
    key = s.lower().strip()
    key = _STRIP_PUNCT.sub("", key)
    key = _JS_SUFFIX.sub("", key).strip()
    key = _VERSION_SUFFIX.sub("", key).strip()
    key = _MULTI_WS.sub(" ", key)
    if vocab and key in vocab:
        return vocab[key]
    return key


# ---------------------------------------------------------------------------
# ESCO vocabulary loader (the only I/O function)
# ---------------------------------------------------------------------------


def load_esco_vocab(path: str) -> dict[str, str]:
    """Load an alias→canonical mapping from a TSV file (alias\\tcanonical)."""
    vocab: dict[str, str] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t", maxsplit=1)
            if len(parts) == 2:
                vocab[parts[0].strip().lower()] = parts[1].strip()
    return vocab


# ---------------------------------------------------------------------------
# Skill-set comparison
# ---------------------------------------------------------------------------


def skills_equal(
    a: list[str],
    b: list[str],
    vocab: dict[str, str] | None = None,
) -> tuple[set[str], set[str], set[str]]:
    """Compare two skill lists in canonical form.

    Returns (true_positives, false_positives, false_negatives).
    *a* is treated as ground truth, *b* as prediction.
    """
    canon_a = {normalize_skill(s, vocab) for s in a}
    canon_b = {normalize_skill(s, vocab) for s in b}
    tp = canon_a & canon_b
    fp = canon_b - canon_a
    fn = canon_a - canon_b
    return tp, fp, fn
