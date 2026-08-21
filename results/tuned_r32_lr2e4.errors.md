# Error analysis — `tuned_r32_lr2e4`

Eval: `/workspace/job-posting-extractor/data/eval/eval_v1.jsonl`  ·  preds: `tuned_r32_lr2e4.preds.jsonl`  ·  n=196

Overall macro-F1: **0.1938**  ·  schema_valid_rate: **1.000**  ·  hallucination_rate: **0.0000**  ·  omission_rate: **0.8175**

## Errors per field

| field | hallucination | omission | wrong_value | total | field_f1 |
| --- | --- | --- | --- | --- | --- |
| title | 0 | 196 | 0 | 196 | 0.000 |
| seniority | 0 | 193 | 0 | 193 | 0.000 |
| contract_type | 0 | 0 | 30 | 30 | 0.847 |
| workload | 0 | 196 | 0 | 196 | 0.000 |
| salary_min | 0 | 169 | 0 | 169 | 0.000 |
| salary_max | 0 | 169 | 0 | 169 | 0.000 |
| salary_period | 0 | 169 | 0 | 169 | 0.000 |
| currency | 0 | 1 | 0 | 1 | 0.997 |
| remote_policy | 0 | 192 | 0 | 192 | 0.000 |
| location_city | 0 | 174 | 0 | 174 | 0.000 |
| location_country | 0 | 195 | 0 | 195 | 0.000 |
| required_skills | 0 | 196 | 0 | 196 | 0.000 |
| nice_to_have_skills | 0 | 164 | 0 | 164 | 0.000 |
| years_experience_min | 0 | 108 | 0 | 108 | 0.000 |
| languages | 0 | 23 | 81 | 104 | 0.257 |
| visa_sponsorship | 0 | 0 | 0 | 0 | 1.000 |

## Macro-F1 by difficulty

| difficulty | macro_f1 | n |
| --- | --- | --- |
| adversarial | 0.1875 | 4 |
| clean | 0.1939 | 192 |

## Macro-F1 by source

| source | macro_f1 | n |
| --- | --- | --- |
| synth_de | 0.1938 | 196 |

## Worst fields — example dumps

Five fields with the most errors: `title`, `workload`, `required_skills`, `location_country`, `seniority`.

### `title` (196 errors)

#### 1. `synth_de_0000` — omission (source=synth_de, difficulty=clean)

- **gold:** `Lead Data Engineer (m/w/d)`
- **pred:** `null`
- **excerpt:**

```
# Lead Data Engineer (m/w/d)  **Altwerk GmbH | Essen | Vollzeit | unbefristet**  #…
```

#### 2. `synth_de_0002` — omission (source=synth_de, difficulty=clean)

- **gold:** `Data Engineer (Senior & Mid-Level)`
- **pred:** `null`
- **excerpt:**

```
# Data Engineering bei Starklab – Zwei Positionen, eine Mission 🚀  **Standort:** Frankfurt am Main   **Umfang:** Vollzeit, unbefristet   **Beginn:** Ab sofort  …
```

#### 3. `synth_de_0003` — omission (source=synth_de, difficulty=clean)

- **gold:** `Junior Data Scientist (m/w/d)`
- **pred:** `null`
- **excerpt:**

```
**GRÜNFLOW GMBH**  Junior Data Scientist (m/w/d)  ---  | **Standort** | Remote / deutschlandweit | …
```

#### 4. `synth_de_0004` — omission (source=synth_de, difficulty=clean)

- **gold:** `Junior Data Analyst (M/W/D)`
- **pred:** `null`
- **excerpt:**

```
JUNIOR DATA ANALYST (M/W/D) – TEILZEIT  Feingrid GmbH | München  ABOUT US  Wir s…
```

#### 5. `synth_de_0006` — omission (source=synth_de, difficulty=clean)

- **gold:** `Principal Data Analyst (m/w/d) – Remote`
- **pred:** `null`
- **excerpt:**

```
# Principal Data Analyst (m/w/d) – Remote 🚀  Frankenplan e.V. | Vollzeit | unbefri…
```

#### 6. `synth_de_0007` — omission (source=synth_de, difficulty=clean)

- **gold:** `Werkstudent Business Analyst (m/w/d) – Darmstadt`
- **pred:** `null`
- **excerpt:**

```
Werkstudent Business Analyst (m/w/d) – Darmstadt  Hey! 👋  Du suchst nach einem s…
```

#### 7. `synth_de_0008` — omission (source=synth_de, difficulty=clean)

- **gold:** `Lead Data Engineer (m/w/d)`
- **pred:** `null`
- **excerpt:**

```
Blaulab AG – Lead Data Engineer (m/w/d) in München  STELLENPROFIL  Die Blaulab AG ist ein Sof…
```

#### 8. `synth_de_0009` — omission (source=synth_de, difficulty=clean)

- **gold:** `HEAD OF DATA ANALYST (M/W/D)`
- **pred:** `null`
- **excerpt:**

```
HEAD OF DATA ANALYST (M/W/D)  Bayernlogik GmbH | Vollzeit, unbefristet | Remote …
```

#### 9. `synth_de_0010` — omission (source=synth_de, difficulty=clean)

- **gold:** `Head of Machine Learning Engineer (m/w/d)`
- **pred:** `null`
- **excerpt:**

```
# Head of Machine Learning Engineer (m/w/d)  **Starknet SE | Berlin | Vollzeit | u…
```

#### 10. `synth_de_0011` — omission (source=synth_de, difficulty=clean)

- **gold:** `Data Analyst (Berufseinsteiger)`
- **pred:** `null`
- **excerpt:**

```
**Data Analyst (Berufseinsteiger) – Starkbasis AG**  Starkbasis AG entwickelt Open…
```

### `workload` (196 errors)

#### 1. `synth_de_0000` — omission (source=synth_de, difficulty=clean)

- **gold:** `full_time`
- **pred:** `null`
- **excerpt:**

```
# Lead Data Engineer (m/w/d)  **Altwerk GmbH | Essen | Vollzeit | unbefristet**  ## Über uns  Altwerk GmbH ist eine Ausgründung der Universität Duisburg-Essen u…
```

#### 2. `synth_de_0002` — omission (source=synth_de, difficulty=clean)

- **gold:** `full_time`
- **pred:** `null`
- **excerpt:**

```
# Data Engineering bei Starklab – Zwei Positionen, eine Mission 🚀  **Standort:** Frankfurt am Main   **Umfang:** Vollzeit, unbefristet   **Beginn:** Ab sofort  …
```

#### 3. `synth_de_0003` — omission (source=synth_de, difficulty=clean)

- **gold:** `full_time`
- **pred:** `null`
- **excerpt:**

```
**GRÜNFLOW GMBH**  Junior Data Scientist (m/w/d)  ---  | **Standort** | Remote / deutschlandweit | |---|---| | **Beschäftigungsart** | Vollzeit, unbefristet | |…
```

#### 4. `synth_de_0004` — omission (source=synth_de, difficulty=clean)

- **gold:** `part_time`
- **pred:** `null`
- **excerpt:**

```
JUNIOR DATA ANALYST (M/W/D) – TEILZEIT  Feingrid GmbH | München  ABOUT US  Wir sind eine Ausgründung der TU München, spezialisiert auf Datenmodellierung für aka…
```

#### 5. `synth_de_0006` — omission (source=synth_de, difficulty=clean)

- **gold:** `full_time`
- **pred:** `null`
- **excerpt:**

```
# Principal Data Analyst (m/w/d) – Remote 🚀  Frankenplan e.V. | Vollzeit | unbefristet | München (Remote)  ---  ## Über uns  Wir sind Frankenplan – ein schlanke…
```

#### 6. `synth_de_0007` — omission (source=synth_de, difficulty=clean)

- **gold:** `part_time`
- **pred:** `null`
- **excerpt:**

```
Werkstudent Business Analyst (m/w/d) – Darmstadt  Hey! 👋  Du suchst nach einem spannenden Einstieg ins Data & Analytics Business? Bei Pflanzvision bekommst Du g…
```

#### 7. `synth_de_0008` — omission (source=synth_de, difficulty=clean)

- **gold:** `part_time`
- **pred:** `null`
- **excerpt:**

```
Blaulab AG – Lead Data Engineer (m/w/d) in München  STELLENPROFIL  Die Blaulab AG ist ein Softwarehaus, das Informationssysteme für Behörden und öffentliche Ins…
```

#### 8. `synth_de_0009` — omission (source=synth_de, difficulty=clean)

- **gold:** `full_time`
- **pred:** `null`
- **excerpt:**

```
HEAD OF DATA ANALYST (M/W/D)  Bayernlogik GmbH | Vollzeit, unbefristet | Remote (Deutschland)  UNTERNEHMEN  Bayernlogik GmbH entwickelt Datenplattformen für die…
```

#### 9. `synth_de_0010` — omission (source=synth_de, difficulty=clean)

- **gold:** `full_time`
- **pred:** `null`
- **excerpt:**

```
# Head of Machine Learning Engineer (m/w/d)  **Starknet SE | Berlin | Vollzeit | unbefristet**  ---  ## Das Unternehmen  Seit drei Generationen entwickelt Stark…
```

#### 10. `synth_de_0011` — omission (source=synth_de, difficulty=clean)

- **gold:** `full_time`
- **pred:** `null`
- **excerpt:**

```
**Data Analyst (Berufseinsteiger) – Starkbasis AG**  Starkbasis AG entwickelt Open-Source-Datenplattformen für Weltraumforschung und Satellitenüberwachung. Wir …
```

### `required_skills` (196 errors)

#### 1. `synth_de_0000` — omission (source=synth_de, difficulty=clean)

- **gold:** `["Apache Airflow", "Oracle SQL", "SAS", "SAP", "DAX", "AWS", "Python"]`
- **pred:** `[]`
- **excerpt:**

```
…d:  - Architektur und Weiterentwicklung unserer ETL-Infrastruktur auf Basis von Apache Airflow (aktuelle Version 2.6) - Verwaltung und Optimierung von Oracle-Da…
```

#### 2. `synth_de_0002` — omission (source=synth_de, difficulty=clean)

- **gold:** `["AWS", "Airflow", "Python", "R", "SQL", "Git", "Docker", "Terraform", "PostgreSQL"]`
- **pred:** `[]`
- **excerpt:**

```
… Underwriting um 30% zu beschleunigen – indem wir alte Batch-Prozesse durch ein Airflow-basiertes Event-Streaming-System ersetzt haben. Das ist die Art von Arbe…
```

#### 3. `synth_de_0003` — omission (source=synth_de, difficulty=clean)

- **gold:** `["Python", "SQL", "Snowflake", "Go", "Power BI", "MySQL"]`
- **pred:** `[]`
- **excerpt:**

```
…rformance-Daten. Deine Aufgaben:  - Extraktion und Transformation von Daten aus Snowflake-Data-Warehouses (aktuelle Version 7.x) - Entwicklung von Datenmodellen…
```

#### 4. `synth_de_0004` — omission (source=synth_de, difficulty=clean)

- **gold:** `["MongoDB", "PostgreSQL", "JavaScript", "Node.js", "Git", "GitHub", "Confluence"]`
- **pred:** `[]`
- **excerpt:**

```
…nsmetadaten. Schwerpunkt liegt auf der Datenaufbereitung aus NoSQL-Datenbanken (MongoDB 5.0) und der Erstellung von Dashboards für unsere Kundinnen und Kunden. …
```

#### 5. `synth_de_0006` — omission (source=synth_de, difficulty=clean)

- **gold:** `["Python", "PostgreSQL", "AWS", "scikit-learn", "pandas", "numpy", "EC2", "RDS", "S3", "Lambda", "IAM", "Java", "C#", "JavaScript", "Excel", "Git", "Terminal"]`
- **pred:** `[]`
- **excerpt:**

```
…sieren möchten.  Gegründet 2019, haben wir mittlerweile ein solides Toolkit aus Python-Pipelines, PostgreSQL-Datenbanken und AWS-Infrastruktur aufgebaut – und j…
```

#### 6. `synth_de_0007` — omission (source=synth_de, difficulty=clean)

- **gold:** `["PostgreSQL", "GCP", "BigQuery", "GitLab", "Git"]`
- **pred:** `[]`
- **excerpt:**

```
…Geschäftsprozesse von innen heraus zu verstehen. Das bedeutet: Du arbeitest mit PostgreSQL an Datenbanken, analysierst Produktivitätsmetriken unserer Kunden und…
```

#### 7. `synth_de_0008` — omission (source=synth_de, difficulty=clean)

- **gold:** `["Apache Spark", "Git", "Jenkins", "Python", "Scala", "C#", "PyTorch"]`
- **pred:** `[]`
- **excerpt:**

```
…litätsstatistiken - Code-Review und technische Richtlinienentwicklung für unser Git-Repository (GitLab self-hosted) - Setup und Wartung unserer Jenkins-CI/CD-Pi…
```

#### 8. `synth_de_0009` — omission (source=synth_de, difficulty=clean)

- **gold:** `["SQL", "Java", "Python", "numpy", "pandas", "Airflow", "Snowflake", "Hadoop", "Confluence"]`
- **pred:** `[]`
- **excerpt:**

```
…). Deine Aufgaben:  • Architektur und Weiterentwicklung unserer Datenpipelines (Airflow 2.5, auf Basis von Kubernetes) • Verantwortung für Data-Quality-Standard…
```

#### 9. `synth_de_0010` — omission (source=synth_de, difficulty=clean)

- **gold:** `["BigQuery", "SQL", "Python", "TensorFlow 2.x", "scikit-learn", "MLOps", "Data Pipelines", "React", "VBA"]`
- **pred:** `[]`
- **excerpt:**

```
…che Guidance - Architektur und Entwicklung von ML-Modellen für Schüleranalysen (BigQuery als primäre Datenquelle) - Verantwortung für den gesamten ML-Lifecycle:…
```

#### 10. `synth_de_0011` — omission (source=synth_de, difficulty=clean)

- **gold:** `["PostgreSQL", "MySQL", "Power BI", "Databricks", "Apache Spark", "Terraform", "Git"]`
- **pred:** `[]`
- **excerpt:**

```
…daten zu erkennen.  **Deine Aufgaben:** Datenbereinigung und -transformation in PostgreSQL und MySQL, Erstellung von interaktiven Power-BI-Dashboards für Missio…
```

### `location_country` (195 errors)

#### 1. `synth_de_0000` — omission (source=synth_de, difficulty=clean)

- **gold:** `DE`
- **pred:** `null`
- **excerpt:**

```
…ssen | Vollzeit | unbefristet**  ## Über uns  Altwerk GmbH ist eine Ausgründung der Universität Duisburg-Essen und arbeitet im Auftrag verschiedener Bundesminis…
```

#### 2. `synth_de_0002` — omission (source=synth_de, difficulty=clean)

- **gold:** `DE`
- **pred:** `null`
- **excerpt:**

```
…teninfrastrukturen für die Versicherungswirtschaft – nicht weil es sexy ist, sondern weil die Branche echte Probleme mit ihren Datensilos hat. Wir helfen mittle…
```

#### 3. `synth_de_0003` — omission (source=synth_de, difficulty=clean)

- **gold:** `DE`
- **pred:** `null`
- **excerpt:**

```
…*GRÜNFLOW GMBH**  Junior Data Scientist (m/w/d)  ---  | **Standort** | Remote / deutschlandweit | |---|---| | **Beschäftigungsart** | Vollzeit, unbefristet | | …
```

#### 4. `synth_de_0004` — omission (source=synth_de, difficulty=clean)

- **gold:** `DE`
- **pred:** `null`
- **excerpt:**

```
…M/W/D) – TEILZEIT  Feingrid GmbH | München  ABOUT US  Wir sind eine Ausgründung der TU München, spezialisiert auf Datenmodellierung für akademische Publikations…
```

#### 5. `synth_de_0006` — omission (source=synth_de, difficulty=clean)

- **gold:** `DE`
- **pred:** `null`
- **excerpt:**

```
…n (Remote)  ---  ## Über uns  Wir sind Frankenplan – ein schlankes, vollständig dezentrales Team von etwa 35 Menschen, die Pharmaziefirmen dabei helfen, ihre Li…
```

#### 6. `synth_de_0007` — omission (source=synth_de, difficulty=clean)

- **gold:** `DE`
- **pred:** `null`
- **excerpt:**

```
Werkstudent Business Analyst (m/w/d) – Darmstadt  Hey! 👋  Du suchst nach einem spannend…
```

#### 7. `synth_de_0008` — omission (source=synth_de, difficulty=clean)

- **gold:** `DE`
- **pred:** `null`
- **excerpt:**

```
…ENPROFIL  Die Blaulab AG ist ein Softwarehaus, das Informationssysteme für Behörden und öffentliche Institutionen im Tourismus- und Reisewesen entwickelt und be…
```

#### 8. `synth_de_0009` — omission (source=synth_de, difficulty=clean)

- **gold:** `DE`
- **pred:** `null`
- **excerpt:**

```
…EAD OF DATA ANALYST (M/W/D)  Bayernlogik GmbH | Vollzeit, unbefristet | Remote (Deutschland)  UNTERNEHMEN  Bayernlogik GmbH entwickelt Datenplattformen für die …
```

#### 9. `synth_de_0010` — omission (source=synth_de, difficulty=clean)

- **gold:** `DE`
- **pred:** `null`
- **excerpt:**

```
… Schulen und Bildungseinrichtungen. Mit knapp 300 Mitarbeitern unterstützen wir deutschlandweit über 2.000 Schulen dabei, Unterricht digitaler und schülerorient…
```

#### 10. `synth_de_0011` — omission (source=synth_de, difficulty=clean)

- **gold:** `DE`
- **pred:** `null`
- **excerpt:**

```
…orschung und Satellitenüberwachung. Wir arbeiten mit europäischen Raumfahrtbehörden zusammen und finanzieren uns durch öffentliche Mittel und Spendenbeiträge. D…
```

### `seniority` (193 errors)

#### 1. `synth_de_0000` — omission (source=synth_de, difficulty=clean)

- **gold:** `lead`
- **pred:** `null`
- **excerpt:**

```
# Lead Data Engineer (m/w/d)  **Altwerk GmbH | Essen | Vollzeit | unbefristet**  #…
```

#### 2. `synth_de_0003` — omission (source=synth_de, difficulty=clean)

- **gold:** `junior`
- **pred:** `null`
- **excerpt:**

```
**GRÜNFLOW GMBH**  Junior Data Scientist (m/w/d)  ---  | **Standort** | Remote / deutschlandweit | …
```

#### 3. `synth_de_0004` — omission (source=synth_de, difficulty=clean)

- **gold:** `junior`
- **pred:** `null`
- **excerpt:**

```
JUNIOR DATA ANALYST (M/W/D) – TEILZEIT  Feingrid GmbH | München  ABOUT US  Wir s…
```

#### 4. `synth_de_0006` — omission (source=synth_de, difficulty=clean)

- **gold:** `senior`
- **pred:** `null`
- **excerpt:**

```
# Principal Data Analyst (m/w/d) – Remote 🚀  Frankenplan e.V. | Vollzeit | unbefristet | München (Remote)  ---  ## Über uns  Wir sind Frankenplan – ein schlanke…
```

#### 5. `synth_de_0007` — omission (source=synth_de, difficulty=clean)

- **gold:** `intern`
- **pred:** `null`
- **excerpt:**

```
Werkstudent Business Analyst (m/w/d) – Darmstadt  Hey! 👋  Du suchst nach einem spannenden Einstieg ins Data & Analytics Business? Bei Pflanzvision bekommst Du g…
```

#### 6. `synth_de_0008` — omission (source=synth_de, difficulty=clean)

- **gold:** `lead`
- **pred:** `null`
- **excerpt:**

```
Blaulab AG – Lead Data Engineer (m/w/d) in München  STELLENPROFIL  Die Blaulab AG ist ein Sof…
```

#### 7. `synth_de_0009` — omission (source=synth_de, difficulty=clean)

- **gold:** `head`
- **pred:** `null`
- **excerpt:**

```
HEAD OF DATA ANALYST (M/W/D)  Bayernlogik GmbH | Vollzeit, unbefristet | Remote …
```

#### 8. `synth_de_0010` — omission (source=synth_de, difficulty=clean)

- **gold:** `head`
- **pred:** `null`
- **excerpt:**

```
# Head of Machine Learning Engineer (m/w/d)  **Starknet SE | Berlin | Vollzeit | u…
```

#### 9. `synth_de_0011` — omission (source=synth_de, difficulty=clean)

- **gold:** `junior`
- **pred:** `null`
- **excerpt:**

```
**Data Analyst (Berufseinsteiger) – Starkbasis AG**  Starkbasis AG entwickelt Open-Source-Datenplattformen für Weltraumforschung und Satellitenüberwachung. Wir …
```

#### 10. `synth_de_0012` — omission (source=synth_de, difficulty=clean)

- **gold:** `lead`
- **pred:** `null`
- **excerpt:**

```
## Lead Data Scientist (m/w/d)  **Starkdata SE** | Berlin | Vollzeit, unbefristet  …
```

