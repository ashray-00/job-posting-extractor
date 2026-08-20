import pytest

from src.normalize import normalize_text, parse_money, normalize_skill, skills_equal


# ---------------------------------------------------------------------------
# parse_money
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("65.000 €", 65_000),
        ("€65,000", 65_000),
        ("65k", 65_000),
        ("65K", 65_000),
        ("ab 65.000", 65_000),
        ("$120,000", 120_000),
        ("EUR 85 000", 85_000),
        ("Gehalt nach Vereinbarung", None),
        ("competitive salary", None),
        ("", None),
    ],
)
def test_parse_money(raw: str, expected: int | None):
    assert parse_money(raw) == expected


# ---------------------------------------------------------------------------
# normalize_text
# ---------------------------------------------------------------------------

def test_normalize_text_basics():
    assert normalize_text("  Hello   World  ") == "hello world"
    assert normalize_text("caf\u00e9") == "café"
    assert normalize_text("a\u200bb\u00a0c") == "a b c"


# ---------------------------------------------------------------------------
# normalize_skill
# ---------------------------------------------------------------------------

def test_normalize_skill_strips_js_and_versions():
    assert normalize_skill("ReactJS") == normalize_skill("React.js")
    assert normalize_skill("python3") == "python"
    assert normalize_skill("Node.js") == "node"
    assert normalize_skill("C++") == "c"


def test_normalize_skill_with_vocab():
    vocab = {"react": "React", "reactjs": "React", "js": "JavaScript"}
    assert normalize_skill("ReactJS", vocab) == "React"
    assert normalize_skill("react.js", vocab) == "React"


# ---------------------------------------------------------------------------
# skills_equal
# ---------------------------------------------------------------------------

def test_skills_equal():
    truth = ["Python", "React.js", "SQL"]
    pred = ["python", "ReactJS", "Docker"]
    tp, fp, fn = skills_equal(truth, pred)
    assert "python" in tp
    assert "react" in tp
    assert "docker" in fp
    assert "sql" in fn
