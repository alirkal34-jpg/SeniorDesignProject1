# SeniorDesignProject1

## Current Progress(22-07-2026)

- Created a candidate dataset containing 100 smartphone products.
- Defined a stable 12-column product data schema.
- Implemented structural schema validation.
- Implemented text and numeric data standardization.
- Implemented non-null, duplicate, and numeric-range validation rules.
- Generated processed CSV and JSON outputs.
- Generated a separate validation issues report.

## Project overview

This repository contains the first-stage data pipeline and search-result
evaluation prototype for the Senior Design Project. The current implementation
works with a 100-product smartphone dataset and provides:

- `DataProcessor` functionality for schema validation, cleaning,
  standardization, and row-level validation.
- A dataset-level quality check for row count, product ID coverage, duplicate
  IDs, and duplicate product variants.
- Selenium-based Google search-result collection for a single product and
  keyword.
- Rule-based domain relevance evaluation using the trusted e-commerce domain
  reference file.
- Standardized JSON experiment output containing the product ID, keyword,
  method, runtime, estimated cost, and evaluated results.

## Current method status

The completed prototype is **Selenium + Rule-Based** for one product/keyword.
It collects up to five search results, assigns domain-based relevance scores,
and writes a standardized JSON file under `results/selenium_rule_based/`.

The other comparison methods are planned next steps and are not implemented
yet:

- Tavily
- Agentic
- Selenium + NanoLLM

## Project structure

```text
first-task/
|-- data/
|   |-- raw/                         # Original candidate datasets
|   |-- processed/                   # Cleaned data and validation report
|   `-- reference/
|       `-- trusted_ecommerce_domains.csv
|-- results/
|   `-- selenium_rule_based/         # Standardized example result JSON
|-- src/
|   |-- data_processor.py
|   |-- quality_check.py
|   |-- selenium_collector.py
|   |-- rule_based_evaluator.py
|   `-- run_selenium_rule_based.py
|-- tests/
|   `-- tests/
|       `-- selenium_smoke_test.py
|-- .gitignore
|-- README.md
`-- requirements.txt
```

## Installation

Python 3 with Google Chrome is required. From PowerShell in the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Running the project

Process and validate the 100-product dataset:

```powershell
.\.venv\Scripts\python.exe src\data_processor.py
```

Run the dataset-level quality check:

```powershell
.\.venv\Scripts\python.exe src\quality_check.py
```

Run the rule-based evaluator with its local sample data:

```powershell
.\.venv\Scripts\python.exe src\rule_based_evaluator.py
```

Run the current single-product Selenium + Rule-Based prototype:

```powershell
.\.venv\Scripts\python.exe src\run_selenium_rule_based.py
```

The Selenium pipeline currently uses product `P001` and the keyword
`iPhone 16 Pro Max 256 GB fiyat`. It records `runtime_seconds` and
`estimated_cost_usd` in the output. The rule-based prototype does not call a
paid API, so its estimated cost is currently `0.0` USD.
