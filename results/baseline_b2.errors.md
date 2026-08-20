# Error analysis — `baseline_b2`

Eval: `/Users/ashray/Documents/llm_projects/fine_tuning/data/eval/eval_v1.jsonl`  ·  preds: `baseline_b2.preds.jsonl`  ·  n=196

Overall macro-F1: **0.7520**  ·  schema_valid_rate: **0.903**  ·  hallucination_rate: **0.1270**  ·  omission_rate: **0.1258**

## Errors per field

| field | hallucination | omission | wrong_value | total | field_f1 |
| --- | --- | --- | --- | --- | --- |
| title | 0 | 19 | 27 | 46 | 0.804 |
| seniority | 2 | 18 | 64 | 84 | 0.600 |
| contract_type | 0 | 19 | 8 | 27 | 0.906 |
| workload | 0 | 19 | 2 | 21 | 0.938 |
| salary_min | 0 | 19 | 1 | 20 | 0.934 |
| salary_max | 0 | 20 | 2 | 22 | 0.925 |
| salary_period | 0 | 19 | 0 | 19 | 0.940 |
| currency | 0 | 20 | 0 | 20 | 0.938 |
| remote_policy | 4 | 19 | 2 | 25 | 0.927 |
| location_city | 19 | 18 | 6 | 43 | 0.860 |
| location_country | 1 | 20 | 1 | 22 | 0.938 |
| required_skills | 0 | 19 | 143 | 162 | 0.182 |
| nice_to_have_skills | 2 | 52 | 97 | 151 | 0.108 |
| years_experience_min | 34 | 20 | 4 | 58 | 0.730 |
| languages | 3 | 29 | 70 | 102 | 0.301 |
| visa_sponsorship | 0 | 0 | 0 | 0 | 1.000 |

## Macro-F1 by difficulty

| difficulty | macro_f1 | n |
| --- | --- | --- |
| adversarial | 0.6250 | 4 |
| clean | 0.7538 | 192 |

## Macro-F1 by source

| source | macro_f1 | n |
| --- | --- | --- |
| synth_de | 0.7520 | 196 |

## Worst fields — example dumps

Five fields with the most errors: `required_skills`, `nice_to_have_skills`, `languages`, `seniority`, `years_experience_min`.

### `required_skills` (162 errors)

#### 1. `synth_de_0000` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Apache Airflow", "Oracle SQL", "SAS", "SAP", "DAX", "AWS", "Python"]`
- **pred:** `["Apache Airflow", "Oracle SQL", "SAS", "SAP", "DAX", "AWS"]`
- **excerpt:**

```
…d:  - Architektur und Weiterentwicklung unserer ETL-Infrastruktur auf Basis von Apache Airflow (aktuelle Version 2.6) - Verwaltung und Optimierung von Oracle-Da…
```

#### 2. `synth_de_0003` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Python", "SQL", "Snowflake", "Go", "Power BI", "MySQL"]`
- **pred:** `["Snowflake", "Go", "Power BI", "SQL", "MySQL"]`
- **excerpt:**

```
…rformance-Daten. Deine Aufgaben:  - Extraktion und Transformation von Daten aus Snowflake-Data-Warehouses (aktuelle Version 7.x) - Entwicklung von Datenmodellen…
```

#### 3. `synth_de_0004` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["MongoDB", "PostgreSQL", "JavaScript", "Node.js", "Git", "GitHub", "Confluence"]`
- **pred:** `["MongoDB", "PostgreSQL", "JavaScript", "Node.js", "GitHub", "Confluence"]`
- **excerpt:**

```
…nsmetadaten. Schwerpunkt liegt auf der Datenaufbereitung aus NoSQL-Datenbanken (MongoDB 5.0) und der Erstellung von Dashboards für unsere Kundinnen und Kunden. …
```

#### 4. `synth_de_0007` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["PostgreSQL", "GCP", "BigQuery", "GitLab", "Git"]`
- **pred:** `["PostgreSQL", "GitLab", "GCP", "Analytisches Denken", "Geschäftslogik"]`
- **excerpt:**

```
…Geschäftsprozesse von innen heraus zu verstehen. Das bedeutet: Du arbeitest mit PostgreSQL an Datenbanken, analysierst Produktivitätsmetriken unserer Kunden und…
```

#### 5. `synth_de_0008` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Apache Spark", "Git", "Jenkins", "Python", "Scala", "C#", "PyTorch"]`
- **pred:** `["Git", "Jenkins", "Apache Spark", "C#", "PyTorch"]`
- **excerpt:**

```
…litätsstatistiken - Code-Review und technische Richtlinienentwicklung für unser Git-Repository (GitLab self-hosted) - Setup und Wartung unserer Jenkins-CI/CD-Pi…
```

#### 6. `synth_de_0009` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["SQL", "Java", "Python", "numpy", "pandas", "Airflow", "Snowflake", "Hadoop", "Confluence"]`
- **pred:** `["SQL", "Java", "Python", "Airflow", "Snowflake", "Hadoop", "Confluence"]`
- **excerpt:**

```
…). Deine Aufgaben:  • Architektur und Weiterentwicklung unserer Datenpipelines (Airflow 2.5, auf Basis von Kubernetes) • Verantwortung für Data-Quality-Standard…
```

#### 7. `synth_de_0010` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["BigQuery", "SQL", "Python", "TensorFlow 2.x", "scikit-learn", "MLOps", "Data Pipelines", "React", "VBA"]`
- **pred:** `["BigQuery", "SQL", "React", "VBA", "MLOps", "Data Pipelines", "Python", "TensorFlow", "scikit-learn"]`
- **excerpt:**

```
…che Guidance - Architektur und Entwicklung von ML-Modellen für Schüleranalysen (BigQuery als primäre Datenquelle) - Verantwortung für den gesamten ML-Lifecycle:…
```

#### 8. `synth_de_0011` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["PostgreSQL", "MySQL", "Power BI", "Databricks", "Apache Spark", "Terraform", "Git"]`
- **pred:** `["PostgreSQL", "MySQL", "Power BI", "Databricks", "Terraform", "Git"]`
- **excerpt:**

```
…daten zu erkennen.  **Deine Aufgaben:** Datenbereinigung und -transformation in PostgreSQL und MySQL, Erstellung von interaktiven Power-BI-Dashboards für Missio…
```

#### 9. `synth_de_0012` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["SQL Server", "Docker", "AWS Redshift", "Looker", "Jenkins", "DAX", "Python", "Git", "Team Leadership", "Mentoring"]`
- **pred:** `["SQL Server", "Docker", "AWS Redshift", "Looker", "Jenkins", "DAX", "Python", "Git"]`
- **excerpt:**

```
…gig sein.  ### Kernaufgaben  - Entwicklung und Optimierung von ETL-Prozessen in SQL Server und AWS Redshift - Aufbau von CI/CD-Pipelines mit Jenkins für automat…
```

#### 10. `synth_de_0015` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["SAS", "BigQuery", "SSIS", "Linux", "Git", "GitLab", "Jira", "SAP", "SQL", "ETL"]`
- **pred:** `["SAS", "BigQuery", "SSIS", "Linux", "GitLab", "Jira", "SAP", "SQL", "ETL"]`
- **excerpt:**

```
…ch Maschinenbau und Fertigungstechnik. Wir unterstützen unsere Kunden bei der Digitalisierung von Verwaltungsprozessen und der Datenverarbeitung in produktionsn…
```

### `nice_to_have_skills` (151 errors)

#### 1. `synth_de_0007` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Python", "SQL", "Looker", "Tableau", "Airflow"]`
- **pred:** `["Python", "SQL", "Dashboard-Tools", "Pharma-Branchenkenntnisse"]`
- **excerpt:**

```
…tsprozesse von innen heraus zu verstehen. Das bedeutet: Du arbeitest mit PostgreSQL an Datenbanken, analysierst Produktivitätsmetriken unserer Kunden und bereit…
```

#### 2. `synth_de_0008` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Kubernetes", "Docker", "SQL Server", "PostgreSQL", "public procurement"]`
- **pred:** `["Kubernetes", "Docker", "SQL Server", "PostgreSQL"]`
- **excerpt:**

```
…n und deren IT-Anforderungen - Kenntnisse von Tourismus- oder Verkehrsdomänen - Kubernetes oder Docker für Containerisierung - SQL Server oder PostgreSQL Admini…
```

#### 3. `synth_de_0012` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Cybersecurity", "Threat Intelligence", "Airflow", "dbt", "PostgreSQL", "Spark"]`
- **pred:** `["Cybersecurity", "Airflow", "dbt", "PostgreSQL", "Spark"]`
- **excerpt:**

```
…unbefristet  ---  ## Über uns  Starkdata SE entwickelt Dateninfrastrukturen für Cybersecurity-Organisationen im Non-Profit-Sektor. Wir unterstützen NGOs und sta…
```

#### 4. `synth_de_0015` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["React", "Data Governance", "SAS Certification", "Government projects"]`
- **pred:** `["Behördenprojekte", "Data-Governance", "SAS-Zertifizierung"]`
- **excerpt:**

```
…sen und Datenqualitätsstandards - Enge Zusammenarbeit mit unserem Backend-Team (React, Linux-basiert) - Unterstützung bei der Migration bestehender SAS-Prozesse…
```

#### 5. `synth_de_0017` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Git", "Docker", "Monitoring", "SAS"]`
- **pred:** `["Git", "Docker", "Metriken/Monitoring"]`
- **excerpt:**

```
…eif machen - Linux-basierte Deployment-Prozesse (Container, systemd) betreuen - SAS-Skripte von älteren Business-Analyseprozessen ablösen und neu implementieren…
```

#### 6. `synth_de_0019` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Python", "Apache Spark", "Airflow", "Tableau", "Healthcare industry experience", "Data warehouse concepts"]`
- **pred:** `["Apache Spark", "Airflow", "Healthcare/regulated industry experience", "Tableau"]`
- **excerpt:**

```
…understanding) - Intermediate PowerPoint skills for stakeholder communication - Python or similar scripting language (beneficial but not mandatory) - Understand…
```

#### 7. `synth_de_0020` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Real estate sector experience", "Financial sector experience", "AWS", "GCP", "Cloud infrastructure"]`
- **pred:** `["Cloud-Infrastrukturen", "AWS", "GCP", "Immobilien- oder Finanzsektor"]`
- **excerpt:**

```
…utsch und gutes Englisch in Wort und Schrift  Wünschenswert sind Erfahrungen im Immobilien- oder Finanzsektor sowie Kenntnisse von Cloud-Infrastrukturen (AWS, G…
```

#### 8. `synth_de_0021` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Time series data", "IoT", "Feature Engineering", "Anomaly Detection"]`
- **pred:** `["Time Series Data", "IoT"]`
- **excerpt:**

```
…olide Grundlagen in Python, GCP-Services und scikit-learn mit, verstehst, warum Feature Engineering kein Luxus ist, und kannst JavaScript genug lesen und schrei…
```

#### 9. `synth_de_0022` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["SAS", "SAS Certification"]`
- **pred:** `["SAS-Zertifikation"]`
- **excerpt:**

```
…Lab und die Evaluierung neuer Frameworks fallen in Ihren Verantwortungsbereich. SAS und VBA werden für Legacy-Systeme und Datenaufbereitung eingesetzt; JavaScri…
```

#### 10. `synth_de_0023` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Hardware knowledge", "Measurement technology"]`
- **pred:** `["Hardware", "Messtechnik"]`
- **excerpt:**

```
…nsere Dokumentation und Code-Reviews laufen zu 60% auf Englisch) - Interesse an Hardwarethemen und Messtechnik ist ein Plus, aber nicht Voraussetzung - Verlässl…
```

### `languages` (102 errors)

#### 1. `synth_de_0000` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "C1"}, {"lang": "en", "level": "C1"}]`
- **pred:** `[{"lang": "de", "level": "C1"}, {"lang": "en", "level": "B2"}]`
- **excerpt:**

```
# Lead Data Engineer (m/w/d)  **Altwerk GmbH | Essen | Vollzeit | unbefristet**  ## Über uns…
```

#### 2. `synth_de_0003` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "B1"}, {"lang": "en", "level": "B1"}]`
- **pred:** `[{"lang": "de", "level": "C1"}, {"lang": "en", "level": "B2"}]`
- **excerpt:**

```
**GRÜNFLOW GMBH**  Junior Data Scientist (m/w/d)  ---  | **Standort** | Remote / deutschlandweit | |---|---| | **B…
```

#### 3. `synth_de_0007` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "B2"}, {"lang": "en", "level": "B1"}]`
- **pred:** `[{"lang": "de", "level": "C1"}, {"lang": "en", "level": "B1"}]`
- **excerpt:**

```
Werkstudent Business Analyst (m/w/d) – Darmstadt  Hey! 👋  Du suchst nach einem spannend…
```

#### 4. `synth_de_0009` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "native"}, {"lang": "en", "level": "B2"}]`
- **pred:** `[{"lang": "de", "level": "C1"}, {"lang": "en", "level": "B2"}]`
- **excerpt:**

```
…EAD OF DATA ANALYST (M/W/D)  Bayernlogik GmbH | Vollzeit, unbefristet | Remote (Deutschland)  UNTERNEHMEN  Bayernlogik GmbH entwickelt Datenplattformen für die …
```

#### 5. `synth_de_0012` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "B2"}]`
- **pred:** `[{"lang": "de", "level": "C1"}]`
- **excerpt:**

```
…r Team besteht aus 24 Personen; die Data & Analytics-Abteilung hat 6 Mitarbeitende.  ---  ## Die Rolle  Du verantwortgest die technische Leitung unserer Datenve…
```

#### 6. `synth_de_0015` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "C1"}, {"lang": "en", "level": "C1"}]`
- **pred:** `[{"lang": "de", "level": "C1"}, {"lang": "en", "level": "B2"}]`
- **excerpt:**

```
## Senior Data Analyst (m/w/d)  **Sachsenlab SE** | Hamburg | Vollzeit, unbefristet …
```

#### 7. `synth_de_0018` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "B2"}, {"lang": "en", "level": "B2"}]`
- **pred:** `[{"lang": "de", "level": "C1"}, {"lang": "en", "level": "B2"}]`
- **excerpt:**

```
## Praktikant Data Scientist (m/w/d)  **Schwabenflow GmbH & Co. KG**  ---  ## Über uns  Wir entwickeln…
```

#### 8. `synth_de_0023` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "en", "level": "B2"}, {"lang": "de", "level": "B1"}]`
- **pred:** `[{"lang": "en", "level": "B1"}]`
- **excerpt:**

```
JUNIOR DATA ENGINEER (M/W/D)  Klarpunkt SE sucht zum nächstmöglichen Termin einen Junior Dat…
```

#### 9. `synth_de_0026` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "B2"}, {"lang": "en", "level": "B2"}]`
- **pred:** `[{"lang": "de", "level": "C1"}, {"lang": "en", "level": "B2"}]`
- **excerpt:**

```
**Junior Software Engineer (m/w/d) – Data Engineering**  Südlogik e.V. ist ein Beratungsunternehme…
```

#### 10. `synth_de_0028` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "B2"}, {"lang": "en", "level": "B2"}]`
- **pred:** `[{"lang": "de", "level": "C1"}, {"lang": "en", "level": "B2"}]`
- **excerpt:**

```
KLARBASIS GMBH | JUNIOR SENIOR DATA ENGINEER (M/W/D)  UNTERNEHMEN  Klarbasis entwickelt Softwarelösungen …
```

### `seniority` (84 errors)

#### 1. `synth_de_0009` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `head`
- **pred:** `lead`
- **excerpt:**

```
HEAD OF DATA ANALYST (M/W/D)  Bayernlogik GmbH | Vollzeit, unbefristet | Remote …
```

#### 2. `synth_de_0010` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `head`
- **pred:** `senior`
- **excerpt:**

```
# Head of Machine Learning Engineer (m/w/d)  **Starknet SE | Berlin | Vollzeit | u…
```

#### 3. `synth_de_0025` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `lead`
- **pred:** `senior`
- **excerpt:**

```
**Principal Cloud Engineer (m/w/d)**  **Altpunkt AG | Frankfurt am Main | Vollzeit | unbefristet**  Wir digitalisieren die Energiewirtschaft von innen heraus. B…
```

#### 4. `synth_de_0028` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `mid`
- **pred:** `junior`
- **excerpt:**

```
KLARBASIS GMBH | JUNIOR SENIOR DATA ENGINEER (M/W/D)  UNTERNEHMEN  Klarbasis entwickelt Softwarel…
```

#### 5. `synth_de_0031` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `mid`
- **pred:** `junior`
- **excerpt:**

```
**Data Analyst (m/w/d) – Nordmind SE, Berlin**  Wir sind Nordmind, ein junges Startup aus Berlin, das sich auf cloudbasierte Datenplattformen für Landwirtschaft…
```

#### 6. `synth_de_0035` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `mid`
- **pred:** `junior`
- **excerpt:**

```
HANSEMEDIA AG SUCHT JUNIOR SENIOR DATA ANALYST (M/W/D)  Wer sind wir?  Hansemedia AG ist 2016 aus de…
```

#### 7. `synth_de_0036` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `lead`
- **pred:** `senior`
- **excerpt:**

```
# Lead Senior Data Engineer (m/w/d) – Teilzeit  **Frankenflow e.V.** | Remote | Ha…
```

#### 8. `synth_de_0039` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `lead`
- **pred:** `senior`
- **excerpt:**

```
**Head of Data Analyst (m/w/d)**  **Sachsentech GmbH | Berlin | Vollzeit | unbefristet**  ---  **Über uns:**  Sachsentech entwickelt seit März 2023 Dateninfrast…
```

#### 9. `synth_de_0040` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `junior`
- **pred:** `intern`
- **excerpt:**

```
**Data Analyst (m/w/d) für die Telekommunikation – Dein Einstieg bei Feincode**  Feincode GmbH & Co. KG ist ein junges Unternehmen aus Hamburg, das sich auf maß…
```

#### 10. `synth_de_0041` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `mid`
- **pred:** `junior`
- **excerpt:**

```
…ation von ML-Outputs in kundengerichtete React-Anwendungen - Mentoring von zwei Junior Data Engineers in unserem Team  ---  **Anforderungen**  **Technical Skill…
```

### `years_experience_min` (58 errors)

#### 1. `synth_de_0092` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `1`
- **pred:** `0`
- **excerpt:**

```
# 🏗️ Software Engineer (m/w/d) für Cloud-basierte Immobilienverwaltung  **Starkkern GmbH & Co. KG | München | Vollzeit, unbefristet**  ---  ## Das Projekt  Wir …
```

#### 2. `synth_de_0094` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `2`
- **pred:** `0`
- **excerpt:**

```
BLAUWARE AG  DATA SCIENTIST (M/W/D)  STELLENORT Köln  BESCHÄFTIGUNGSFORM Vollzeit, unbefristet  VERGÜTUNG 75.804 € – 101.359 € Jahresbrutto je nach Qualifikatio…
```

#### 3. `synth_de_0151` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `2`
- **pred:** `0`
- **excerpt:**

```
# SACHSENLINK SE SUCHT: PRINCIPAL DATA ANALYST (M/W/D)  **Dein zukünftiger Arbeitsort: Hannover | Vollzeit, unbefristet**  ---  ## WER WIR SIND  Sachsenlink – d…
```

#### 4. `synth_de_0167` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `2`
- **pred:** `0`
- **excerpt:**

```
# Junior Data Analyst (m/w/d)  **Altmind GmbH & Co. KG | Köln | Vollzeit | unbefristet**  ---  ## Das Unternehmen  Altmind revolutioniert die Landwirtschaftstec…
```

#### 5. `synth_de_0003` — hallucination (source=synth_de, difficulty=clean)

- **gold:** `null`
- **pred:** `0`
- **excerpt:**

```
**GRÜNFLOW GMBH**  Junior Data Scientist (m/w/d)  ---  | **Standort** | Remote / deutschlandweit | |---|---| | **Beschäftigungsart** | Vollzeit, unbefristet | |…
```

#### 6. `synth_de_0004` — hallucination (source=synth_de, difficulty=clean)

- **gold:** `null`
- **pred:** `0`
- **excerpt:**

```
JUNIOR DATA ANALYST (M/W/D) – TEILZEIT  Feingrid GmbH | München  ABOUT US  Wir sind eine Ausgründung der TU München, spezialisiert auf Datenmodellierung für aka…
```

#### 7. `synth_de_0012` — hallucination (source=synth_de, difficulty=clean)

- **gold:** `null`
- **pred:** `0`
- **excerpt:**

```
## Lead Data Scientist (m/w/d)  **Starkdata SE** | Berlin | Vollzeit, unbefristet  ---  ## Über uns  Starkdata SE entwickelt Dateninfrastrukturen für Cybersecur…
```

#### 8. `synth_de_0016` — hallucination (source=synth_de, difficulty=clean)

- **gold:** `null`
- **pred:** `0`
- **excerpt:**

```
**Werkstudent Data Scientist**  **Über uns**  Nordplan GmbH & Co. KG entwickelt seit 2023 Backend-Systeme und Dateninfrastruktur für Browser-basierte Multiplaye…
```

#### 9. `synth_de_0017` — hallucination (source=synth_de, difficulty=clean)

- **gold:** `null`
- **pred:** `0`
- **excerpt:**

```
# Software Engineer (m/w/d) – Berufseinsteiger  **Starkmedia UG** | Hamburg  ---  ## Quick Facts  | | | |---|---| | **Standort** | Hamburg (Altstadt) | | **Anst…
```

#### 10. `synth_de_0019` — hallucination (source=synth_de, difficulty=clean)

- **gold:** `null`
- **pred:** `0`
- **excerpt:**

```
JUNIOR DATA ENGINEER (M/W/D) – ULMER INNOVATIONSZENTRUM  Nordvision AG entwickelt seit über 35 Jahren Medizintechnik-Systeme, die in mehr als 8.000 Krankenhäuse…
```

