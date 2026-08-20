# Cross-model comparison — `baseline_b1` vs `baseline_b2`

Eval: `/Users/ashray/Documents/llm_projects/fine_tuning/data/eval/eval_v1.jsonl`

- Fields where **baseline_b1 right / baseline_b2 wrong**: **4**
- Fields where **baseline_b2 right / baseline_b1 wrong**: **16**

## baseline_b1 right, baseline_b2 wrong

| field | count |
| --- | --- |
| years_experience_min | 2 |
| languages | 1 |
| required_skills | 1 |

Showing up to 40 examples:

1. `synth_de_0032` · `years_experience_min` · gold=`null` · baseline_b1=`null` · baseline_b2=`0`
2. `synth_de_0149` · `languages` · gold=`[{"lang": "de", "level": "B1"}, {"lang": "en", "level": "B1"}]` · baseline_b1=`[{"lang": "de", "level": "B1"}, {"lang": "en", "level": "B1"}]` · baseline_b2=`[{"lang": "de", "level": "C1"}, {"lang": "en", "level": "B1"}]`
3. `synth_de_0199` · `years_experience_min` · gold=`null` · baseline_b1=`null` · baseline_b2=`0`
4. `synth_de_0096` · `required_skills` · gold=`["Jupyter", "Redshift", "Oracle", "SAS", "SQL", "Git", "Python", "R"]` · baseline_b1=`["Redshift", "Oracle", "SAS", "SQL", "Jupyter", "Git", "Python", "R"]` · baseline_b2=`["Jupyter notebooks", "Redshift", "Oracle", "SAS", "SQL", "Git", "Python", "R"]`

## baseline_b2 right, baseline_b1 wrong

| field | count |
| --- | --- |
| remote_policy | 3 |
| seniority | 3 |
| languages | 3 |
| contract_type | 2 |
| title | 1 |
| nice_to_have_skills | 1 |
| location_city | 1 |
| visa_sponsorship | 1 |
| required_skills | 1 |

Showing up to 40 examples:

1. `synth_de_0032` · `title` · gold=`Senior Data Analyst (m/w/d) – Berufseinsteiger willkommen` · baseline_b1=`Senior Data Analyst (m/w/d)` · baseline_b2=`Senior Data Analyst (m/w/d) – Berufseinsteiger willkommen`
2. `synth_de_0032` · `nice_to_have_skills` · gold=`["AWS", "Azure"]` · baseline_b1=`["GCP", "AWS", "Azure"]` · baseline_b2=`["AWS", "Azure"]`
3. `synth_de_0036` · `contract_type` · gold=`permanent` · baseline_b1=`part_time` · baseline_b2=`permanent`
4. `synth_de_0050` · `remote_policy` · gold=`remote` · baseline_b1=`fully_remote` · baseline_b2=`remote`
5. `synth_de_0050` · `location_city` · gold=`null` · baseline_b1=`remote` · baseline_b2=`null`
6. `synth_de_0063` · `visa_sponsorship` · gold=`True` · baseline_b1=`yes` · baseline_b2=`True`
7. `synth_de_0087` · `remote_policy` · gold=`hybrid` · baseline_b1=`flexible` · baseline_b2=`hybrid`
8. `synth_de_0088` · `seniority` · gold=`senior` · baseline_b1=`principal` · baseline_b2=`senior`
9. `synth_de_0101` · `required_skills` · gold=`["MATLAB", "NumPy", "Pandas", "Docker", "Git", "Python"]` · baseline_b1=`["MATLAB", "NumPy", "Pandas", "Docker", "Git", "Python", "SQL"]` · baseline_b2=`["MATLAB", "NumPy", "Pandas", "Docker", "Git", "Python"]`
10. `synth_de_0169` · `contract_type` · gold=`internship` · baseline_b1=`intern` · baseline_b2=`internship`
11. `synth_de_0184` · `remote_policy` · gold=`remote` · baseline_b1=`fully_remote` · baseline_b2=`remote`
12. `synth_de_0078` · `languages` · gold=`[{"lang": "de", "level": "B2"}, {"lang": "en", "level": "B1"}]` · baseline_b1=`[{"lang": "de", "level": "B2"}, {"lang": "en", "level": "proficient"}]` · baseline_b2=`[{"lang": "de", "level": "B2"}, {"lang": "en", "level": "B1"}]`
13. `synth_de_0113` · `languages` · gold=`[{"lang": "de", "level": "B2"}]` · baseline_b1=`[{"lang": "de", "level": "B2+"}]` · baseline_b2=`[{"lang": "de", "level": "B2"}]`
14. `synth_de_0140` · `seniority` · gold=`senior` · baseline_b1=`principal` · baseline_b2=`senior`
15. `synth_de_0151` · `seniority` · gold=`senior` · baseline_b1=`principal` · baseline_b2=`senior`
16. `synth_de_0178` · `languages` · gold=`[{"lang": "de", "level": "B2"}]` · baseline_b1=`[{"lang": "de", "level": "B2+"}]` · baseline_b2=`[{"lang": "de", "level": "B2"}]`

