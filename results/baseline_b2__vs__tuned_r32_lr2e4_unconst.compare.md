# Cross-model comparison — `baseline_b2` vs `tuned_r32_lr2e4_unconst`

Eval: `/Users/ashray/Documents/llm_projects/fine_tuning/data/eval/eval_v1.jsonl`

- Fields where **baseline_b2 right / tuned_r32_lr2e4_unconst wrong**: **187**
- Fields where **tuned_r32_lr2e4_unconst right / baseline_b2 wrong**: **351**

## baseline_b2 right, tuned_r32_lr2e4_unconst wrong

| field | count |
| --- | --- |
| title | 43 |
| contract_type | 23 |
| nice_to_have_skills | 20 |
| required_skills | 20 |
| languages | 19 |
| seniority | 17 |
| years_experience_min | 16 |
| location_country | 11 |
| remote_policy | 8 |
| location_city | 7 |
| workload | 2 |
| salary_min | 1 |

Showing up to 40 examples:

1. `synth_de_0002` · `seniority` · gold=`null` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`senior`
2. `synth_de_0007` · `contract_type` · gold=`working_student` · baseline_b2=`working_student` · tuned_r32_lr2e4_unconst=`internship`
3. `synth_de_0007` · `workload` · gold=`part_time` · baseline_b2=`part_time` · tuned_r32_lr2e4_unconst=`full_time`
4. `synth_de_0009` · `title` · gold=`HEAD OF DATA ANALYST (M/W/D)` · baseline_b2=`Head of Data Analyst (M/W/D)` · tuned_r32_lr2e4_unconst=`Head of Data Analyst`
5. `synth_de_0009` · `nice_to_have_skills` · gold=`["JavaScript"]` · baseline_b2=`["JavaScript"]` · tuned_r32_lr2e4_unconst=`["JavaScript", "Hadoop", "Confluence"]`
6. `synth_de_0011` · `seniority` · gold=`junior` · baseline_b2=`junior` · tuned_r32_lr2e4_unconst=`null`
7. `synth_de_0011` · `location_country` · gold=`DE` · baseline_b2=`DE` · tuned_r32_lr2e4_unconst=`null`
8. `synth_de_0011` · `nice_to_have_skills` · gold=`["Python"]` · baseline_b2=`["Python"]` · tuned_r32_lr2e4_unconst=`["Python", "Databricks", "Apache Spark", "Git"]`
9. `synth_de_0011` · `years_experience_min` · gold=`0` · baseline_b2=`0` · tuned_r32_lr2e4_unconst=`null`
10. `synth_de_0011` · `languages` · gold=`[{"lang": "de", "level": "C1"}]` · baseline_b2=`[{"lang": "de", "level": "C1"}]` · tuned_r32_lr2e4_unconst=`[{"lang": "de", "level": "B1"}]`
11. `synth_de_0015` · `salary_min` · gold=`102004` · baseline_b2=`102004` · tuned_r32_lr2e4_unconst=`10204`
12. `synth_de_0016` · `contract_type` · gold=`working_student` · baseline_b2=`working_student` · tuned_r32_lr2e4_unconst=`internship`
13. `synth_de_0016` · `languages` · gold=`[{"lang": "en", "level": "B2"}]` · baseline_b2=`[{"lang": "en", "level": "B2"}]` · tuned_r32_lr2e4_unconst=`[{"lang": "en", "level": "B1"}]`
14. `synth_de_0017` · `required_skills` · gold=`["Python", "SQL", "Kafka", "Linux", "PyTorch", "scikit-learn"]` · baseline_b2=`["Python", "SQL", "Kafka", "Linux", "PyTorch", "scikit-learn"]` · tuned_r32_lr2e4_unconst=`["Python", "SQL", "Kafka", "PostgreSQL", "PyTorch", "scikit-learn", "Linux"]`
15. `synth_de_0022` · `location_country` · gold=`DE` · baseline_b2=`DE` · tuned_r32_lr2e4_unconst=`null`
16. `synth_de_0023` · `title` · gold=`Junior Data Engineer (M/W/D)` · baseline_b2=`Junior Data Engineer (m/w/d)` · tuned_r32_lr2e4_unconst=`Junior Data Engineer`
17. `synth_de_0023` · `years_experience_min` · gold=`0` · baseline_b2=`0` · tuned_r32_lr2e4_unconst=`null`
18. `synth_de_0026` · `years_experience_min` · gold=`0` · baseline_b2=`0` · tuned_r32_lr2e4_unconst=`null`
19. `synth_de_0029` · `nice_to_have_skills` · gold=`[]` · baseline_b2=`[]` · tuned_r32_lr2e4_unconst=`["AWS", "Scala"]`
20. `synth_de_0030` · `seniority` · gold=`intern` · baseline_b2=`intern` · tuned_r32_lr2e4_unconst=`junior`
21. `synth_de_0031` · `nice_to_have_skills` · gold=`[]` · baseline_b2=`[]` · tuned_r32_lr2e4_unconst=`["DAX", "MongoDB"]`
22. `synth_de_0032` · `title` · gold=`Senior Data Analyst (m/w/d) – Berufseinsteiger willkommen` · baseline_b2=`Senior Data Analyst (m/w/d) – Berufseinsteiger willkommen` · tuned_r32_lr2e4_unconst=`Senior Data Analyst (m/w/d)`
23. `synth_de_0033` · `title` · gold=`Praktikant Data Analyst (m/w/d)` · baseline_b2=`Praktikant Data Analyst (M/W/D)` · tuned_r32_lr2e4_unconst=`Data Analyst`
24. `synth_de_0033` · `seniority` · gold=`intern` · baseline_b2=`intern` · tuned_r32_lr2e4_unconst=`junior`
25. `synth_de_0033` · `contract_type` · gold=`internship` · baseline_b2=`internship` · tuned_r32_lr2e4_unconst=`permanent`
26. `synth_de_0035` · `title` · gold=`Junior Senior Data Analyst (M/W/D)` · baseline_b2=`Junior Senior Data Analyst (m/w/d)` · tuned_r32_lr2e4_unconst=`Junior Senior Data Analyst`
27. `synth_de_0036` · `contract_type` · gold=`permanent` · baseline_b2=`permanent` · tuned_r32_lr2e4_unconst=`contract`
28. `synth_de_0038` · `title` · gold=`Praktikant Senior Data Analyst (m/w/d)` · baseline_b2=`Praktikant Senior Data Analyst (m/w/d)` · tuned_r32_lr2e4_unconst=`Praktikant Senior Data Analyst`
29. `synth_de_0038` · `seniority` · gold=`intern` · baseline_b2=`intern` · tuned_r32_lr2e4_unconst=`junior`
30. `synth_de_0038` · `required_skills` · gold=`["Hadoop", "C++", "C#", "Go", "Qlik", "SQL", "Git"]` · baseline_b2=`["Hadoop", "C++", "C#", "Go", "Qlik", "SQL", "Git"]` · tuned_r32_lr2e4_unconst=`["Hadoop", "Qlik", "SQL", "Git"]`
31. `synth_de_0038` · `nice_to_have_skills` · gold=`[]` · baseline_b2=`[]` · tuned_r32_lr2e4_unconst=`["C++", "C#", "Go"]`
32. `synth_de_0039` · `title` · gold=`Head of Data Analyst (m/w/d)` · baseline_b2=`Head of Data Analyst (m/w/d)` · tuned_r32_lr2e4_unconst=`Head of Data Analyst`
33. `synth_de_0039` · `nice_to_have_skills` · gold=`["IIoT", "SQL Performance Tuning", "Agile"]` · baseline_b2=`["IIoT", "SQL Performance Tuning", "Agile"]` · tuned_r32_lr2e4_unconst=`["IIoT", "SQL", "Agile"]`
34. `synth_de_0040` · `required_skills` · gold=`["SQL Server", "C++", "Linux", "SAP", "NumPy", "Excel"]` · baseline_b2=`["SQL Server", "C++", "Linux", "SAP", "NumPy", "Excel"]` · tuned_r32_lr2e4_unconst=`["SQL Server", "C++", "Linux", "SAP", "NumPy", "Excel", "VBA"]`
35. `synth_de_0040` · `years_experience_min` · gold=`0` · baseline_b2=`0` · tuned_r32_lr2e4_unconst=`null`
36. `synth_de_0043` · `required_skills` · gold=`["Tableau", "SSIS", "Python", "Pandas", "NumPy", "Scikit-learn", "Kubernetes"]` · baseline_b2=`["Tableau", "SSIS", "Python", "Kubernetes", "Pandas", "NumPy", "Scikit-learn"]` · tuned_r32_lr2e4_unconst=`["Tableau", "SSIS", "Python", "Pandas", "NumPy", "Kubernetes"]`
37. `synth_de_0045` · `contract_type` · gold=`permanent` · baseline_b2=`permanent` · tuned_r32_lr2e4_unconst=`internship`
38. `synth_de_0045` · `languages` · gold=`[{"lang": "en", "level": "B2"}]` · baseline_b2=`[{"lang": "en", "level": "B2"}]` · tuned_r32_lr2e4_unconst=`[{"lang": "en", "level": "B1"}]`
39. `synth_de_0048` · `required_skills` · gold=`["Jenkins", "MongoDB", "Docker", "AWS", "SQL", "Python"]` · baseline_b2=`["Jenkins", "MongoDB", "Docker", "AWS", "SQL", "Python"]` · tuned_r32_lr2e4_unconst=`["Python", "SQL", "Jenkins", "MongoDB", "Docker", "AWS", "Kubernetes"]`
40. `synth_de_0049` · `title` · gold=`Machine Learning Engineer (m/w/d) für den Berufsstart` · baseline_b2=`Machine Learning Engineer (m/w/d) für den Berufsstart` · tuned_r32_lr2e4_unconst=`Machine Learning Engineer (m/w/d)`

_… +147 more_

## tuned_r32_lr2e4_unconst right, baseline_b2 wrong

| field | count |
| --- | --- |
| years_experience_min | 49 |
| seniority | 39 |
| location_city | 37 |
| remote_policy | 22 |
| contract_type | 20 |
| salary_max | 20 |
| location_country | 20 |
| salary_period | 19 |
| currency | 19 |
| title | 19 |
| workload | 18 |
| salary_min | 18 |
| required_skills | 18 |
| languages | 18 |
| nice_to_have_skills | 15 |

Showing up to 40 examples:

1. `synth_de_0002` · `contract_type` · gold=`permanent` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`permanent`
2. `synth_de_0002` · `workload` · gold=`full_time` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`full_time`
3. `synth_de_0002` · `salary_min` · gold=`76405` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`76405`
4. `synth_de_0002` · `salary_max` · gold=`99720` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`99720`
5. `synth_de_0002` · `salary_period` · gold=`year` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`year`
6. `synth_de_0002` · `currency` · gold=`EUR` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`EUR`
7. `synth_de_0002` · `remote_policy` · gold=`hybrid` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`hybrid`
8. `synth_de_0002` · `location_city` · gold=`Frankfurt am Main` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`Frankfurt am Main`
9. `synth_de_0002` · `location_country` · gold=`DE` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`DE`
10. `synth_de_0007` · `required_skills` · gold=`["PostgreSQL", "GCP", "BigQuery", "GitLab", "Git"]` · baseline_b2=`["PostgreSQL", "GitLab", "GCP", "Analytisches Denken", "Geschäftslogik"]` · tuned_r32_lr2e4_unconst=`["PostgreSQL", "GCP", "GitLab", "Git", "BigQuery"]`
11. `synth_de_0009` · `seniority` · gold=`head` · baseline_b2=`lead` · tuned_r32_lr2e4_unconst=`head`
12. `synth_de_0009` · `location_city` · gold=`null` · baseline_b2=`Deutschland` · tuned_r32_lr2e4_unconst=`null`
13. `synth_de_0010` · `seniority` · gold=`head` · baseline_b2=`senior` · tuned_r32_lr2e4_unconst=`head`
14. `synth_de_0011` · `location_city` · gold=`null` · baseline_b2=`Berlin` · tuned_r32_lr2e4_unconst=`null`
15. `synth_de_0012` · `nice_to_have_skills` · gold=`["Cybersecurity", "Threat Intelligence", "Airflow", "dbt", "PostgreSQL", "Spark"]` · baseline_b2=`["Cybersecurity", "Airflow", "dbt", "PostgreSQL", "Spark"]` · tuned_r32_lr2e4_unconst=`["Cybersecurity", "Threat Intelligence", "Airflow", "dbt", "PostgreSQL", "Spark"]`
16. `synth_de_0012` · `years_experience_min` · gold=`null` · baseline_b2=`0` · tuned_r32_lr2e4_unconst=`null`
17. `synth_de_0012` · `languages` · gold=`[{"lang": "de", "level": "B2"}]` · baseline_b2=`[{"lang": "de", "level": "C1"}]` · tuned_r32_lr2e4_unconst=`[{"lang": "de", "level": "B2"}]`
18. `synth_de_0013` · `seniority` · gold=`senior` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`senior`
19. `synth_de_0013` · `contract_type` · gold=`permanent` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`permanent`
20. `synth_de_0013` · `workload` · gold=`full_time` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`full_time`
21. `synth_de_0013` · `salary_min` · gold=`88885` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`88885`
22. `synth_de_0013` · `salary_max` · gold=`102716` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`102716`
23. `synth_de_0013` · `salary_period` · gold=`year` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`year`
24. `synth_de_0013` · `currency` · gold=`EUR` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`EUR`
25. `synth_de_0013` · `location_city` · gold=`Berlin` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`Berlin`
26. `synth_de_0013` · `location_country` · gold=`DE` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`DE`
27. `synth_de_0013` · `years_experience_min` · gold=`5` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`5`
28. `synth_de_0016` · `remote_policy` · gold=`null` · baseline_b2=`hybrid` · tuned_r32_lr2e4_unconst=`null`
29. `synth_de_0016` · `location_city` · gold=`null` · baseline_b2=`Berlin` · tuned_r32_lr2e4_unconst=`null`
30. `synth_de_0016` · `location_country` · gold=`null` · baseline_b2=`DE` · tuned_r32_lr2e4_unconst=`null`
31. `synth_de_0016` · `years_experience_min` · gold=`null` · baseline_b2=`0` · tuned_r32_lr2e4_unconst=`null`
32. `synth_de_0017` · `years_experience_min` · gold=`null` · baseline_b2=`0` · tuned_r32_lr2e4_unconst=`null`
33. `synth_de_0019` · `years_experience_min` · gold=`null` · baseline_b2=`0` · tuned_r32_lr2e4_unconst=`null`
34. `synth_de_0022` · `remote_policy` · gold=`null` · baseline_b2=`hybrid` · tuned_r32_lr2e4_unconst=`null`
35. `synth_de_0022` · `location_city` · gold=`null` · baseline_b2=`nicht angegeben` · tuned_r32_lr2e4_unconst=`null`
36. `synth_de_0024` · `title` · gold=`Data Scientist (m/w/d) für Agrarwirtschaft` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`Data Scientist (m/w/d) für Agrarwirtschaft`
37. `synth_de_0024` · `seniority` · gold=`mid` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`mid`
38. `synth_de_0024` · `contract_type` · gold=`permanent` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`permanent`
39. `synth_de_0024` · `workload` · gold=`full_time` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`full_time`
40. `synth_de_0024` · `salary_min` · gold=`105269` · baseline_b2=`null` · tuned_r32_lr2e4_unconst=`105269`

_… +311 more_

