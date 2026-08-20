from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


Seniority = Literal["intern", "junior", "mid", "senior", "lead", "head"]
ContractType = Literal["permanent", "fixed_term", "contract", "internship", "working_student"]
Workload = Literal["full_time", "part_time"]
SalaryPeriod = Literal["year", "month", "hour"]
RemotePolicy = Literal["onsite", "hybrid", "remote"]
LanguageLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2", "native"]


class LanguageRequirement(BaseModel):
    lang: str
    level: LanguageLevel

    @field_validator("lang")
    @classmethod
    def lang_is_two_letter(cls, v: str) -> str:
        if len(v) != 2 or not v.isalpha():
            raise ValueError("lang must be a 2-letter code")
        return v


class JobPosting(BaseModel):
    title: Optional[str] = None
    seniority: Optional[Seniority] = None
    contract_type: Optional[ContractType] = None
    workload: Optional[Workload] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_period: Optional[SalaryPeriod] = None
    currency: Optional[str] = None
    remote_policy: Optional[RemotePolicy] = None
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    required_skills: list[str] = []
    nice_to_have_skills: list[str] = []
    years_experience_min: Optional[int] = None
    languages: list[LanguageRequirement] = []
    visa_sponsorship: Optional[bool] = None

    @field_validator("currency")
    @classmethod
    def currency_is_iso4217(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (len(v) != 3 or not v.isalpha() or not v.isupper()):
            raise ValueError("currency must be exactly 3 uppercase letters (ISO 4217)")
        return v

    @field_validator("location_country")
    @classmethod
    def country_is_iso3166(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (len(v) != 2 or not v.isalpha() or not v.isupper()):
            raise ValueError("location_country must be exactly 2 uppercase letters (ISO 3166-1 alpha-2)")
        return v

    @model_validator(mode="after")
    def salary_range_valid(self) -> JobPosting:
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("salary_min must be <= salary_max")
        return self


JOB_POSTING_JSON_SCHEMA = JobPosting.model_json_schema()
