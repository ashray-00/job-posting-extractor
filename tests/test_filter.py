"""One crafted reject-case per filter rule; each fails only that rule."""
from __future__ import annotations

import copy

from src.filter import RULES, check


def _base(**overrides) -> dict:
    """A fully grounded, valid document that passes all rules."""
    text = (
        "Senior Backend Engineer (m/w/d) in Berlin. "
        "Full-time permanent role. Hybrid / Home Office possible. "
        "Salary 80.000 – 100.000 € Jahresbrutto. "
        "Required: Python, SQL, Docker. Nice to have: Kubernetes. "
        "At least 5 years of experience. "
        "Languages: English C1, German B2. "
        "Visa sponsorship not available."
    )
    label = {
        "title": "Senior Backend Engineer (m/w/d)",
        "seniority": "senior",
        "contract_type": "permanent",
        "workload": "full_time",
        "salary_min": 80000,
        "salary_max": 100000,
        "salary_period": "year",
        "currency": "EUR",
        "remote_policy": "hybrid",
        "location_city": "Berlin",
        "location_country": "DE",
        "required_skills": ["Python", "SQL", "Docker"],
        "nice_to_have_skills": ["Kubernetes"],
        "years_experience_min": 5,
        "languages": [
            {"lang": "en", "level": "C1"},
            {"lang": "de", "level": "B2"},
        ],
        "visa_sponsorship": False,
    }
    doc = {
        "doc_id": "test_base",
        "text": text,
        "candidate_label": label,
        "source": "test",
        "lang": "en",
    }
    for k, v in overrides.items():
        if k == "candidate_label":
            lab = copy.deepcopy(label)
            lab.update(v)
            doc["candidate_label"] = lab
        else:
            doc[k] = v
    return doc


def test_base_accepted():
    ok, failed = check(_base())
    assert ok, failed
    assert failed == []


def _assert_only(rule_name: str, doc: dict):
    ok, failed = check(doc)
    assert not ok, f"expected rejection for {rule_name}, got accept"
    assert failed == [rule_name], f"expected only [{rule_name}], got {failed}"


def test_reject_schema():
    # invalid enum → schema fail; keep other fields grounded
    doc = _base(candidate_label={"seniority": "not_a_real_level"})
    _assert_only("schema", doc)


def test_reject_salary_order():
    doc = _base(candidate_label={"salary_min": 120000, "salary_max": 80000})
    # still within year bounds, both appear in text? 120000 does NOT appear —
    # so salary_grounded may also fail. Put both numbers in text.
    doc["text"] = (
        "Engineer in Berlin. Hybrid Home Office. "
        "Salary range mentioned as 120.000 € and also 80.000 € somehow inverted. "
        "Required: Python, SQL, Docker. Nice: Kubernetes. "
        "5 years of experience. English and German. Jahresbrutto year."
    )
    doc["candidate_label"]["salary_period"] = "year"
    doc["candidate_label"]["salary_min"] = 120000
    doc["candidate_label"]["salary_max"] = 80000
    _assert_only("salary_order", doc)


def test_reject_salary_plausible():
    # year salary absurdly high; put the number in text so grounded passes
    doc = _base(
        text=(
            "Engineer in Berlin. Hybrid Home Office. "
            "Salary 900.000 € Jahresbrutto per year. "
            "Required: Python, SQL, Docker. Nice: Kubernetes. "
            "5 years of experience. English German."
        ),
        candidate_label={
            "salary_min": 900000,
            "salary_max": 900000,
            "salary_period": "year",
        },
    )
    _assert_only("salary_plausible", doc)


def test_reject_salary_grounded():
    doc = _base(candidate_label={"salary_min": 77777, "salary_max": 88888})
    # text still has 80.000–100.000, not 77777
    _assert_only("salary_grounded", doc)


def test_reject_skills_grounded():
    # >10% ungrounded: 1 of 4 = 25%
    doc = _base(
        candidate_label={
            "required_skills": ["Python", "SQL", "Docker"],
            "nice_to_have_skills": ["QuantumChromodynamics"],
        }
    )
    _assert_only("skills_grounded", doc)


def test_reject_experience_grounded():
    doc = _base(candidate_label={"years_experience_min": 9})
    # text says 5 years, not 9
    _assert_only("experience_grounded", doc)


def test_reject_remote_trigger():
    doc = _base(
        text=(
            "Senior Backend Engineer (m/w/d) in Berlin. "
            "Full-time permanent onsite office only. "
            "Salary 80.000 – 100.000 € Jahresbrutto. "
            "Required: Python, SQL, Docker. Nice to have: Kubernetes. "
            "At least 5 years of experience. "
            "Languages: English C1, German B2."
        ),
        candidate_label={"remote_policy": "remote"},
    )
    _assert_only("remote_trigger", doc)


def test_reject_language_plausible():
    doc = _base(
        candidate_label={
            "languages": [{"lang": "ja", "level": "B1"}],
        }
    )
    # text has English/German, not Japanese
    _assert_only("language_plausible", doc)


def test_reject_city_grounded():
    doc = _base(candidate_label={"location_city": "München"})
    _assert_only("city_grounded", doc)


def test_all_rule_names_covered():
    names = {n for n, _ in RULES}
    expected = {
        "schema",
        "salary_order",
        "salary_plausible",
        "salary_grounded",
        "skills_grounded",
        "experience_grounded",
        "remote_trigger",
        "language_plausible",
        "city_grounded",
    }
    assert names == expected
