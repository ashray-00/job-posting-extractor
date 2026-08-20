import pytest
from pydantic import ValidationError

from schema.posting import JobPosting


def test_fully_populated():
    p = JobPosting(
        title="Senior Backend Engineer",
        seniority="senior",
        contract_type="permanent",
        workload="full_time",
        salary_min=80_000,
        salary_max=120_000,
        salary_period="year",
        currency="EUR",
        remote_policy="hybrid",
        location_city="Berlin",
        location_country="DE",
        required_skills=["Python", "SQL"],
        nice_to_have_skills=["Kubernetes"],
        years_experience_min=5,
        languages=[{"lang": "en", "level": "C1"}, {"lang": "de", "level": "B2"}],
        visa_sponsorship=True,
    )
    assert p.title == "Senior Backend Engineer"
    assert p.salary_min == 80_000
    assert len(p.languages) == 2
    assert p.languages[0].level == "C1"


def test_all_null():
    p = JobPosting()
    assert p.title is None
    assert p.required_skills == []
    assert p.nice_to_have_skills == []
    assert p.languages == []


def test_salary_min_gt_max_fails():
    with pytest.raises(ValidationError, match="salary_min must be <= salary_max"):
        JobPosting(salary_min=100_000, salary_max=50_000)


def test_invalid_currency_fails():
    with pytest.raises(ValidationError, match="currency"):
        JobPosting(currency="EURO")


def test_required_skills_none_fails():
    with pytest.raises(ValidationError):
        JobPosting(required_skills=None)
