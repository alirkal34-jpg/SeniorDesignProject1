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
- Structured OpenRouter/Nano LLM keyword generation for processed products.
- Testable Nano LLM relevance evaluation output for Selenium + NanoLLM.
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
- Selenium + NanoLLM keyword relevance evaluation scaffold

## Project structure

```text
first-task/
|-- data/
|   |-- raw/                         # Original candidate datasets
|   |-- processed/                   # Cleaned data and validation report
|   |-- labels/                      # Human ground-truth templates
|   `-- reference/
|       `-- trusted_ecommerce_domains.csv
|-- results/
|   `-- selenium_rule_based/         # Standardized example result JSON
|-- src/
|   |-- data_processor.py
|   |-- keyword_loader.py
|   |-- keyword_generator.py
|   |-- nano_llm_evaluator.py
|   |-- relevance_evaluator.py
|   |-- quality_check.py
|   |-- selenium_collector.py
|   |-- rule_based_evaluator.py
|   |-- run_rule_based_batch.py
|   |-- run_selenium_nano_llm.py
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

## LLM keyword generation

The selected Nano LLM provider is OpenRouter. The default model is configured
through environment variables:

```text
OPENROUTER_API_KEY=
NANO_LLM_MODEL=google/gemini-flash-1.5-8b
```

Copy `.env.example` to `.env` locally and add the real API key only in `.env`.
Real API keys, tokens, and passwords must not be committed.

Generate a zero-cost local sample for the first three products:

```powershell
.\.venv\Scripts\python.exe src\keyword_generator.py --provider fake --limit 3
```

Generate keywords with OpenRouter:

```powershell
.\.venv\Scripts\python.exe src\keyword_generator.py --provider openrouter --limit 3
```

After the 3-product call is verified, generate the complete 100-product list:

```powershell
.\.venv\Scripts\python.exe src\keyword_generator.py --provider openrouter --limit 100
```

The command prints the elapsed runtime. OpenRouter usage cost is read from the
API response for NanoLLM result files; if the provider does not return a cost,
the recorded value remains `0.0` and the token usage should be retained in the
provider dashboard for reporting.

The structured output is written to:

```text
data/processed/generated_keywords.json
```

Example output:

```json
[
  {
    "product_id": "P001",
    "keyword": "Apple iPhone 16 Pro Max 256 GB fiyat"
  }
]
```

The relevance evaluator keeps the shared result format and adds
`predicted_relevant` plus `relevance_score` fields for each result. Supported
method names are `tavily_llm`, `agentic_search`, `selenium_nano_llm`, and
`selenium_rule_based`.

Validate generated keywords:

```powershell
.\.venv\Scripts\python.exe src\keyword_loader.py --limit 3
```

Run the CAPTCHA-safe Selenium + Rule-Based batch for only the first 2-3
keywords:

```powershell
.\.venv\Scripts\python.exe src\run_rule_based_batch.py --limit 3 --max-results 5
```

Test the NanoLLM evaluator independently with three sample search results:

```powershell
.\.venv\Scripts\python.exe src\nano_llm_evaluator.py --provider fake
```

Run Selenium + NanoLLM for one keyword while reusing `selenium_collector.py`:

```powershell
.\.venv\Scripts\python.exe src\run_selenium_nano_llm.py --provider fake --max-results 5
```

Run the real provider only after the 3-keyword call succeeds:

```powershell
.\.venv\Scripts\python.exe src\run_selenium_nano_llm.py --provider openrouter --max-results 5
```

The human-labeling template for comparing predicted relevance with manual
judgment is:

```text
data/labels/domain_ground_truth.csv
```

Run API-free tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```
