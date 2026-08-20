"""Hand-computed expected values for src.metrics.evaluate."""
from __future__ import annotations

from src.metrics import FIELDS, evaluate


def _full_gold(**overrides):
    """A gold record with all 16 fields non-null (except lists can be filled)."""
    base = {
        "title": "Senior Engineer",
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
        "required_skills": ["Python", "SQL"],
        "nice_to_have_skills": ["Docker"],
        "years_experience_min": 5,
        "languages": [{"lang": "en", "level": "C1"}],
        "visa_sponsorship": True,
    }
    base.update(overrides)
    return base


def test_perfect_predictions():
    gold = _full_gold()
    pred = dict(gold)
    result = evaluate([pred], [gold], vocab={})

    assert result["schema_valid_rate"] == 1.0
    assert result["macro_f1"] == 1.0
    assert result["hallucination_rate"] == 0.0
    assert result["omission_rate"] == 0.0
    assert result["exact_record_match"] == 1.0
    assert result["skill_set_f1"]["f1"] == 1.0
    for field in FIELDS:
        assert result["field_f1"][field]["f1"] == 1.0


def test_all_predictions_null_golds_non_null():
    gold = _full_gold()
    # Explicit all-null prediction (empty lists, None scalars)
    pred = {
        "title": None,
        "seniority": None,
        "contract_type": None,
        "workload": None,
        "salary_min": None,
        "salary_max": None,
        "salary_period": None,
        "currency": None,
        "remote_policy": None,
        "location_city": None,
        "location_country": None,
        "required_skills": [],
        "nice_to_have_skills": [],
        "years_experience_min": None,
        "languages": [],
        "visa_sponsorship": None,
    }
    result = evaluate([pred], [gold], vocab={})

    # Every gold field is non-null → every (example, field) is an omission
    assert result["omission_rate"] == 1.0
    assert result["macro_f1"] == 0.0
    assert result["hallucination_rate"] == 0.0
    assert result["exact_record_match"] == 0.0
    assert result["skill_set_f1"]["recall"] == 0.0
    assert result["skill_set_f1"]["f1"] == 0.0


def test_all_predictions_non_null_golds_all_null():
    gold = {
        "title": None,
        "seniority": None,
        "contract_type": None,
        "workload": None,
        "salary_min": None,
        "salary_max": None,
        "salary_period": None,
        "currency": None,
        "remote_policy": None,
        "location_city": None,
        "location_country": None,
        "required_skills": [],
        "nice_to_have_skills": [],
        "years_experience_min": None,
        "languages": [],
        "visa_sponsorship": None,
    }
    pred = _full_gold()
    result = evaluate([pred], [gold], vocab={})

    # Every gold field is null → every non-null pred is a hallucination
    assert result["hallucination_rate"] == 1.0
    assert result["omission_rate"] == 0.0
    assert result["exact_record_match"] == 0.0


def test_one_field_wrong_out_of_sixteen():
    gold = _full_gold()
    pred = dict(gold)
    pred["seniority"] = "junior"  # wrong; gold is "senior"

    result = evaluate([pred], [gold], vocab={})

    # 15 fields perfect (f1=1), seniority wrong:
    #   both non-null, not equal → correct=0, pred_nn=1, gold_nn=1 → f1=0
    # macro_f1 = 15/16 = 0.9375
    assert result["field_f1"]["seniority"]["f1"] == 0.0
    assert result["field_f1"]["seniority"]["precision"] == 0.0
    assert result["field_f1"]["seniority"]["recall"] == 0.0
    for field in FIELDS:
        if field != "seniority":
            assert result["field_f1"][field]["f1"] == 1.0
    assert result["macro_f1"] == 15 / 16
    assert result["exact_record_match"] == 0.0
    assert result["hallucination_rate"] == 0.0
    assert result["omission_rate"] == 0.0


def test_parse_failure_counts_as_all_null():
    gold = _full_gold()
    result = evaluate([None], [gold], vocab={})

    assert result["schema_valid_rate"] == 0.0
    # Same as all-null prediction against non-null gold
    assert result["omission_rate"] == 1.0
    assert result["macro_f1"] == 0.0
    assert result["hallucination_rate"] == 0.0
    assert result["exact_record_match"] == 0.0

    # Mixed: one valid perfect, one parse failure
    result2 = evaluate([dict(gold), None], [gold, gold], vocab={})
    assert result2["schema_valid_rate"] == 0.5
