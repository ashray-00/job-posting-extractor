# Error analysis — `tuned_r32_lr2e4_unconst`

Eval: `/Users/ashray/Documents/llm_projects/fine_tuning/data/eval/eval_v1.jsonl`  ·  preds: `tuned_r32_lr2e4_unconst.preds.jsonl`  ·  n=196

Overall macro-F1: **0.7755**  ·  schema_valid_rate: **1.000**  ·  hallucination_rate: **0.0332**  ·  omission_rate: **0.0366**

## Errors per field

| field | hallucination | omission | wrong_value | total | field_f1 |
| --- | --- | --- | --- | --- | --- |
| title | 0 | 0 | 70 | 70 | 0.643 |
| seniority | 1 | 22 | 39 | 62 | 0.723 |
| contract_type | 0 | 0 | 30 | 30 | 0.847 |
| workload | 0 | 0 | 5 | 5 | 0.974 |
| salary_min | 0 | 0 | 3 | 3 | 0.982 |
| salary_max | 0 | 0 | 2 | 2 | 0.988 |
| salary_period | 0 | 0 | 0 | 0 | 1.000 |
| currency | 0 | 1 | 0 | 1 | 0.997 |
| remote_policy | 0 | 0 | 11 | 11 | 0.943 |
| location_city | 0 | 2 | 11 | 13 | 0.931 |
| location_country | 0 | 13 | 0 | 13 | 0.966 |
| required_skills | 0 | 0 | 164 | 164 | 0.163 |
| nice_to_have_skills | 14 | 17 | 125 | 156 | 0.135 |
| years_experience_min | 2 | 18 | 5 | 25 | 0.850 |
| languages | 0 | 23 | 80 | 103 | 0.265 |
| visa_sponsorship | 0 | 0 | 0 | 0 | 1.000 |

## Macro-F1 by difficulty

| difficulty | macro_f1 | n |
| --- | --- | --- |
| adversarial | 0.7924 | 4 |
| clean | 0.7751 | 192 |

## Macro-F1 by source

| source | macro_f1 | n |
| --- | --- | --- |
| synth_de | 0.7755 | 196 |

## Worst fields — example dumps

Five fields with the most errors: `required_skills`, `nice_to_have_skills`, `languages`, `title`, `seniority`.

### `required_skills` (164 errors)

#### 1. `synth_de_0000` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Apache Airflow", "Oracle SQL", "SAS", "SAP", "DAX", "AWS", "Python"]`
- **pred:** `["Apache Airflow", "Oracle SQL", "SAS", "SAP", "DAX", "Power BI"]`
- **excerpt:**

```
…d:  - Architektur und Weiterentwicklung unserer ETL-Infrastruktur auf Basis von Apache Airflow (aktuelle Version 2.6) - Verwaltung und Optimierung von Oracle-Da…
```

#### 2. `synth_de_0002` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["AWS", "Airflow", "Python", "R", "SQL", "Git", "Docker", "Terraform", "PostgreSQL"]`
- **pred:** `["AWS", "Airflow", "SQL", "Python", "R", "Git", "GitHub", "PostgreSQL"]`
- **excerpt:**

```
… Underwriting um 30% zu beschleunigen – indem wir alte Batch-Prozesse durch ein Airflow-basiertes Event-Streaming-System ersetzt haben. Das ist die Art von Arbe…
```

#### 3. `synth_de_0004` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["MongoDB", "PostgreSQL", "JavaScript", "Node.js", "Git", "GitHub", "Confluence"]`
- **pred:** `["MongoDB", "PostgreSQL", "JavaScript", "Node.js", "GitHub", "Confluence"]`
- **excerpt:**

```
…nsmetadaten. Schwerpunkt liegt auf der Datenaufbereitung aus NoSQL-Datenbanken (MongoDB 5.0) und der Erstellung von Dashboards für unsere Kundinnen und Kunden. …
```

#### 4. `synth_de_0006` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Python", "PostgreSQL", "AWS", "scikit-learn", "pandas", "numpy", "EC2", "RDS", "S3", "Lambda", "IAM", "Java", "C#", "JavaScript", "Excel", "Git", "Terminal"]`
- **pred:** `["Python", "PostgreSQL", "AWS", "scikit-learn", "C#", "Java", "Excel"]`
- **excerpt:**

```
…sieren möchten.  Gegründet 2019, haben wir mittlerweile ein solides Toolkit aus Python-Pipelines, PostgreSQL-Datenbanken und AWS-Infrastruktur aufgebaut – und j…
```

#### 5. `synth_de_0008` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Apache Spark", "Git", "Jenkins", "Python", "Scala", "C#", "PyTorch"]`
- **pred:** `["Git", "Jenkins", "Apache Spark", "Scala", "Python", "C#"]`
- **excerpt:**

```
…litätsstatistiken - Code-Review und technische Richtlinienentwicklung für unser Git-Repository (GitLab self-hosted) - Setup und Wartung unserer Jenkins-CI/CD-Pi…
```

#### 6. `synth_de_0009` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["SQL", "Java", "Python", "numpy", "pandas", "Airflow", "Snowflake", "Hadoop", "Confluence"]`
- **pred:** `["SQL", "Java", "Python", "Airflow", "Snowflake", "Kubernetes", "ETL", "Data Warehouse"]`
- **excerpt:**

```
…). Deine Aufgaben:  • Architektur und Weiterentwicklung unserer Datenpipelines (Airflow 2.5, auf Basis von Kubernetes) • Verantwortung für Data-Quality-Standard…
```

#### 7. `synth_de_0010` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["BigQuery", "SQL", "Python", "TensorFlow 2.x", "scikit-learn", "MLOps", "Data Pipelines", "React", "VBA"]`
- **pred:** `["BigQuery", "SQL", "React", "Python", "TensorFlow", "scikit-learn", "VBA"]`
- **excerpt:**

```
…che Guidance - Architektur und Entwicklung von ML-Modellen für Schüleranalysen (BigQuery als primäre Datenquelle) - Verantwortung für den gesamten ML-Lifecycle:…
```

#### 8. `synth_de_0011` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["PostgreSQL", "MySQL", "Power BI", "Databricks", "Apache Spark", "Terraform", "Git"]`
- **pred:** `["PostgreSQL", "MySQL", "Power BI", "Terraform", "AWS"]`
- **excerpt:**

```
…daten zu erkennen.  **Deine Aufgaben:** Datenbereinigung und -transformation in PostgreSQL und MySQL, Erstellung von interaktiven Power-BI-Dashboards für Missio…
```

#### 9. `synth_de_0012` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["SQL Server", "Docker", "AWS Redshift", "Looker", "Jenkins", "DAX", "Python", "Git", "Team Leadership", "Mentoring"]`
- **pred:** `["SQL Server", "AWS Redshift", "Docker", "Jenkins", "Looker", "DAX", "Python", "Pandas", "NumPy", "Git"]`
- **excerpt:**

```
…gig sein.  ### Kernaufgaben  - Entwicklung und Optimierung von ETL-Prozessen in SQL Server und AWS Redshift - Aufbau von CI/CD-Pipelines mit Jenkins für automat…
```

#### 10. `synth_de_0013` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Oracle", "SQL", "Terraform", "Python", "Bash", "Linux", "Windows", "Data Modeling", "ETL", "AWS"]`
- **pred:** `["Oracle", "SQL", "Terraform", "AWS", "Python", "Shell", "Tableau", "Metabase"]`
- **excerpt:**

```
…täglich terabyte an Markt-, Transaktions- und Bestandsdaten fehlerlos in unsere Oracle-Datenbanken fließen. Du bist nicht nur Wartungsperson, sondern Architekt …
```

### `nice_to_have_skills` (156 errors)

#### 1. `synth_de_0000` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["SAS Viya", "Power BI", "RFC modules", "SAP Data Services"]`
- **pred:** `["SAS Viya", "AWS", "SAP Data Services"]`
- **excerpt:**

```
… und Performance-Tuning - Praktisches Wissen in **SAS** (SAS/BASE und eventuell SAS Viya) - Konfiguration und Betrieb von **SAP-Schnittstellen** (insbesondere R…
```

#### 2. `synth_de_0002` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Tableau", "Jupyter", "Snowflake", "AWS Certified Data Engineer", "Data Architecture"]`
- **pred:** `["Snowflake", "Tableau", "Jupyter", "Docker", "Terraform", "AWS", "Python", "R"]`
- **excerpt:**

```
…unterschiedlichem Fokus und Verantwortung.  ---  ## Was der Stack aussieht  - **AWS** (S3, Redshift, Lambda, RDS) als Backbone - **Airflow 2.4+** für Orchestrie…
```

#### 3. `synth_de_0006` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["d3.js", "Spark", "Machine Learning", "Healthcare domain knowledge", "Logistics experience", "Infrastructure as code", "Terraform"]`
- **pred:** `["JavaScript", "d3.js"]`
- **excerpt:**

```
…nd Optimierung von ETL-Prozessen für pharmazeutische Bestandsdaten (PostgreSQL, Spark-Jobs auf AWS) - **Komplexe Probleme lösen**: Machine-Learning-Modelle mit …
```

#### 4. `synth_de_0007` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Python", "SQL", "Looker", "Tableau", "Airflow"]`
- **pred:** `["Python", "SQL", "Looker", "Tableau"]`
- **excerpt:**

```
…tsprozesse von innen heraus zu verstehen. Das bedeutet: Du arbeitest mit PostgreSQL an Datenbanken, analysierst Produktivitätsmetriken unserer Kunden und bereit…
```

#### 5. `synth_de_0008` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Kubernetes", "Docker", "SQL Server", "PostgreSQL", "public procurement"]`
- **pred:** `["Kubernetes", "Docker", "SQL Server", "PostgreSQL"]`
- **excerpt:**

```
…n und deren IT-Anforderungen - Kenntnisse von Tourismus- oder Verkehrsdomänen - Kubernetes oder Docker für Containerisierung - SQL Server oder PostgreSQL Admini…
```

#### 6. `synth_de_0009` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["JavaScript"]`
- **pred:** `["JavaScript", "Hadoop", "Confluence"]`
- **excerpt:**

```
…ive Erfahrung mit Airflow (ETL-Orchestrierung) und Snowflake (Data Warehouse) • Hadoop-Ökosystem oder ähnliche Distributed-Systems-Erfahrung • JavaScript für Da…
```

#### 7. `synth_de_0011` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Python"]`
- **pred:** `["Python", "Databricks", "Apache Spark", "Git"]`
- **excerpt:**

```
…eraktiven Power-BI-Dashboards für Missionsleiter, Datenpipeline-Entwicklung mit Databricks (Spark-basiert), Infrastruktur-as-Code mittels Terraform für Cloud-De…
```

#### 8. `synth_de_0015` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["React", "Data Governance", "SAS Certification", "Government projects"]`
- **pred:** `["Behördenprojekten", "Data-Governance", "SAS-Umfeld"]`
- **excerpt:**

```
…sen und Datenqualitätsstandards - Enge Zusammenarbeit mit unserem Backend-Team (React, Linux-basiert) - Unterstützung bei der Migration bestehender SAS-Prozesse…
```

#### 9. `synth_de_0017` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Git", "Docker", "Monitoring", "SAS"]`
- **pred:** `["Git", "Docker", "Metriken", "Monitoring"]`
- **excerpt:**

```
…eif machen - Linux-basierte Deployment-Prozesse (Container, systemd) betreuen - SAS-Skripte von älteren Business-Analyseprozessen ablösen und neu implementieren…
```

#### 10. `synth_de_0019` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `["Python", "Apache Spark", "Airflow", "Tableau", "Healthcare industry experience", "Data warehouse concepts"]`
- **pred:** `["Apache Spark", "Airflow", "Tableau"]`
- **excerpt:**

```
…understanding) - Intermediate PowerPoint skills for stakeholder communication - Python or similar scripting language (beneficial but not mandatory) - Understand…
```

### `languages` (103 errors)

#### 1. `synth_de_0000` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "C1"}, {"lang": "en", "level": "C1"}]`
- **pred:** `[{"lang": "de", "level": "B2"}, {"lang": "en", "level": "B1"}]`
- **excerpt:**

```
# Lead Data Engineer (m/w/d)  **Altwerk GmbH | Essen | Vollzeit | unbefristet**  ## Über uns…
```

#### 2. `synth_de_0003` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "B1"}, {"lang": "en", "level": "B1"}]`
- **pred:** `[{"lang": "de", "level": "B1"}]`
- **excerpt:**

```
**GRÜNFLOW GMBH**  Junior Data Scientist (m/w/d)  ---  | **Standort** | Remote / deutschlandweit | |---|---| | **B…
```

#### 3. `synth_de_0006` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "B2"}, {"lang": "en", "level": "B1"}]`
- **pred:** `[{"lang": "en", "level": "B1"}]`
- **excerpt:**

```
# Principal Data Analyst (m/w/d) – Remote 🚀  Frankenplan e.V. | Vollzeit | unbefristet | München (Remote)  ---  ## Über uns  Wir s…
```

#### 4. `synth_de_0007` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "B2"}, {"lang": "en", "level": "B1"}]`
- **pred:** `[{"lang": "de", "level": "B1"}]`
- **excerpt:**

```
Werkstudent Business Analyst (m/w/d) – Darmstadt  Hey! 👋  Du suchst nach einem spannend…
```

#### 5. `synth_de_0008` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "C1"}]`
- **pred:** `[{"lang": "de", "level": "B2"}]`
- **excerpt:**

```
…ENPROFIL  Die Blaulab AG ist ein Softwarehaus, das Informationssysteme für Behörden und öffentliche Institutionen im Tourismus- und Reisewesen entwickelt und be…
```

#### 6. `synth_de_0009` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "native"}, {"lang": "en", "level": "B2"}]`
- **pred:** `[{"lang": "de", "level": "B2"}, {"lang": "en", "level": "B1"}]`
- **excerpt:**

```
…EAD OF DATA ANALYST (M/W/D)  Bayernlogik GmbH | Vollzeit, unbefristet | Remote (Deutschland)  UNTERNEHMEN  Bayernlogik GmbH entwickelt Datenplattformen für die …
```

#### 7. `synth_de_0011` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "C1"}]`
- **pred:** `[{"lang": "de", "level": "B1"}]`
- **excerpt:**

```
…orschung und Satellitenüberwachung. Wir arbeiten mit europäischen Raumfahrtbehörden zusammen und finanzieren uns durch öffentliche Mittel und Spendenbeiträge. D…
```

#### 8. `synth_de_0015` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "C1"}, {"lang": "en", "level": "C1"}]`
- **pred:** `[{"lang": "de", "level": "B2"}, {"lang": "en", "level": "B2"}]`
- **excerpt:**

```
## Senior Data Analyst (m/w/d)  **Sachsenlab SE** | Hamburg | Vollzeit, unbefristet …
```

#### 9. `synth_de_0016` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "en", "level": "B2"}]`
- **pred:** `[{"lang": "en", "level": "B1"}]`
- **excerpt:**

```
**Werkstudent Data Scientist**  **Über uns**  Nordplan GmbH & Co. KG entwickelt seit 2023 …
```

#### 10. `synth_de_0018` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `[{"lang": "de", "level": "B2"}, {"lang": "en", "level": "B2"}]`
- **pred:** `[{"lang": "de", "level": "B1"}, {"lang": "en", "level": "B1"}]`
- **excerpt:**

```
## Praktikant Data Scientist (m/w/d)  **Schwabenflow GmbH & Co. KG**  ---  ## Über uns  Wir entwickeln…
```

### `title` (70 errors)

#### 1. `synth_de_0002` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `Data Engineer (Senior & Mid-Level)`
- **pred:** `Data Engineer (m/w/d) Senior`
- **excerpt:**

```
…on Arbeit, die hier passiert.  Wir suchen **zwei Positionen** parallel: einen **Data Engineer (m/w/d) Senior** (5+ Jahre) und einen **Data Engineer (m/w/d) Mid-…
```

#### 2. `synth_de_0004` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `Junior Data Analyst (M/W/D)`
- **pred:** `JUNIOR DATA ANALYST (M/W/D) – TEILZEIT`
- **excerpt:**

```
JUNIOR DATA ANALYST (M/W/D) – TEILZEIT  Feingrid GmbH | München  ABOUT US  Wir s…
```

#### 3. `synth_de_0006` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `Principal Data Analyst (m/w/d) – Remote`
- **pred:** `Principal Data Analyst (m/w/d)`
- **excerpt:**

```
# Principal Data Analyst (m/w/d) – Remote 🚀  Frankenplan e.V. | Vollzeit | unbefri…
```

#### 4. `synth_de_0007` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `Werkstudent Business Analyst (m/w/d) – Darmstadt`
- **pred:** `Werkstudent Business Analyst (m/w/d)`
- **excerpt:**

```
Werkstudent Business Analyst (m/w/d) – Darmstadt  Hey! 👋  Du suchst nach einem s…
```

#### 5. `synth_de_0009` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `HEAD OF DATA ANALYST (M/W/D)`
- **pred:** `Head of Data Analyst`
- **excerpt:**

```
HEAD OF DATA ANALYST (M/W/D)  Bayernlogik GmbH | Vollzeit, unbefristet | Remote …
```

#### 6. `synth_de_0013` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `Senior Data Analyst (m/w/d)`
- **pred:** `Senior Data Analyst`
- **excerpt:**

```
SPREEPUNKT UG SUCHT SENIOR DATA ANALYST (M/W/D)  Berlin | Vollzeit | Unbefristet  ---  Du bist leide…
```

#### 7. `synth_de_0019` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `Junior Data Engineer (M/W/D) – Ulmer Innovationszentrum`
- **pred:** `Junior Data Engineer`
- **excerpt:**

```
JUNIOR DATA ENGINEER (M/W/D) – ULMER INNOVATIONSZENTRUM  Nordvision AG entwickel…
```

#### 8. `synth_de_0023` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `Junior Data Engineer (M/W/D)`
- **pred:** `Junior Data Engineer`
- **excerpt:**

```
JUNIOR DATA ENGINEER (M/W/D)  Klarpunkt SE sucht zum nächstmöglichen Termin eine…
```

#### 9. `synth_de_0032` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `Senior Data Analyst (m/w/d) – Berufseinsteiger willkommen`
- **pred:** `Senior Data Analyst (m/w/d)`
- **excerpt:**

```
**Senior Data Analyst (m/w/d) – Berufseinsteiger willkommen**  **Schwabencloud UG …
```

#### 10. `synth_de_0033` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `Praktikant Data Analyst (m/w/d)`
- **pred:** `Data Analyst`
- **excerpt:**

```
PRAKTIKANT DATA ANALYST (M/W/D)  Südnet e.V. sucht ab sofort einen leidenschaftl…
```

### `seniority` (62 errors)

#### 1. `synth_de_0025` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `lead`
- **pred:** `senior`
- **excerpt:**

```
**Principal Cloud Engineer (m/w/d)**  **Altpunkt AG | Frankfurt am Main | Vollzeit | unbefristet**  Wir digitalisieren die Energiewirtschaft von innen heraus. B…
```

#### 2. `synth_de_0028` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `mid`
- **pred:** `junior`
- **excerpt:**

```
KLARBASIS GMBH | JUNIOR SENIOR DATA ENGINEER (M/W/D)  UNTERNEHMEN  Klarbasis entwickelt Softwarel…
```

#### 3. `synth_de_0030` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `intern`
- **pred:** `junior`
- **excerpt:**

```
…ergütung mit Übernahmeperspektive (3–4 Positionen pro Jahr) - Zugang zu unserer internen ML-Bibliothek (hauseigene Python-Module für Preprocessing & Feature Eng…
```

#### 4. `synth_de_0031` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `mid`
- **pred:** `junior`
- **excerpt:**

```
**Data Analyst (m/w/d) – Nordmind SE, Berlin**  Wir sind Nordmind, ein junges Startup aus Berlin, das sich auf cloudbasierte Datenplattformen für Landwirtschaft…
```

#### 5. `synth_de_0033` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `intern`
- **pred:** `junior`
- **excerpt:**

```
PRAKTIKANT DATA ANALYST (M/W/D)  Südnet e.V. sucht ab sofort einen leidenschaftlichen Data Analyst für unser Münchener Büro!  DU BIST DER DURCHSTARTER, DEN WIR …
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

#### 8. `synth_de_0038` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `intern`
- **pred:** `junior`
- **excerpt:**

```
PRAKTIKANT SENIOR DATA ANALYST (M/W/D)  Schwabenmind e.V., Berlin  ÜBER UNS  Schwabenmind ist ein IT-Dienstleister des öffentlichen Sektors mit Spezialisierung …
```

#### 9. `synth_de_0039` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `lead`
- **pred:** `head`
- **excerpt:**

```
**Head of Data Analyst (m/w/d)**  **Sachsentech GmbH | Berlin | Vollzeit | unbefri…
```

#### 10. `synth_de_0049` — wrong_value (source=synth_de, difficulty=clean)

- **gold:** `junior`
- **pred:** `mid`
- **excerpt:**

```
# Machine Learning Engineer (m/w/d) für den Berufsstart  **Nordsys SE | Erfurt | Vollzeit | unbefristet**  ## Über uns  Bei Nordsys verwalten wir täglich die Fi…
```

