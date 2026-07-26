# SeniorDesignProject1

## Current Progress (25-07-2026)

- Created a candidate dataset containing 100 smartphone products.
- Defined a stable 12-column product data schema.
- Implemented structural schema validation.
- Implemented text and numeric data standardization.
- Implemented non-null, duplicate, and numeric-range validation rules.
- Generated processed CSV and JSON outputs.
- Generated a separate validation issues report.
- Added a product-specific HTTPS reference lookup URL for every dataset row.
- Added initial AI-assisted relevance labels for every currently stored
  search result and enabled preliminary accuracy calculation.

## Project overview

This repository contains the first-stage data pipeline and search-result
evaluation prototype for the Senior Design Project. The current implementation
works with a 100-product smartphone dataset and provides:

- `DataProcessor` functionality for schema validation, cleaning,
  standardization, and row-level validation.
- A dataset-level quality check for row count, product ID coverage, duplicate
  IDs, duplicate product variants, and complete HTTPS source references.
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
|   |-- evaluation/                  # Fixed 10-product pilot subset
|   |-- labels/                      # Human ground-truth labels
|   `-- reference/
|       `-- trusted_ecommerce_domains.csv
|-- results/
|   |-- selenium_nano_llm/           # Fake-provider example result JSON
|   `-- selenium_rule_based/         # Standardized example result JSON
|-- src/
|   |-- evaluation/                  # Schema, labels, and metrics utilities
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

Every current product row includes a product-specific GSMArena search URL in
`source_url`. These URLs are reference locators for follow-up specification
verification; they do not claim that every dataset value was originally
copied from GSMArena.

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

The human-labeling template for comparing predicted relevance with manual
judgment is:

```text
data/labels/domain_ground_truth.csv
```

Run API-free tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Evaluation utilities

The repository includes API-free utilities for validating result files and
preparing the final comparison:

- `src/evaluation/result_validator.py` checks the shared experiment JSON
  schema and rejects missing fields, invalid method names, negative
  runtime/cost values, invalid URLs, non-boolean predictions, and relevance
  scores outside the `0-1` range.
- `src/evaluation/metrics.py` calculates experiment count, result count,
  average runtime, total/average estimated cost, relevant-result ratio,
  ground-truth coverage, confusion counts, and accuracy for each method.
- `src/evaluation/ground_truth.py` loads human relevance labels and supports
  shared labels so that the same URL does not need to be labeled separately
  for every method.
- `data/evaluation/evaluation_subset.csv` defines a representative pilot set
  of 10 products from 10 different brands.

## Evaluation protocol

The following rules are fixed for the final method comparison and must be
applied consistently to Selenium + Rule-Based, Selenium + NanoLLM,
Tavily + NanoLLM, and Agentic Search.

### Human relevance rule

A search result is **relevant** when it matches the phone model specified in
the keyword and, when present, the requested storage capacity, and has a
transactional purpose such as a retailer product page, marketplace listing,
classified listing, or price-comparison page.

A result is **irrelevant** when it refers to the wrong model, the wrong storage
capacity, an accessory, a news article, or a review page. An exact matching
product remains relevant when it is temporarily out of stock.

### Fixed experiment settings

- Use the same 10-product subset from
  `data/evaluation/evaluation_subset.csv`.
- Assign one fixed keyword to each evaluation product.
- Pass each product's keyword to all four methods without changing its text.
- Collect at most five results per product and method (`max_results = 5`).
- Use a relevance threshold of `0.60`. The Rule-Based implementation stores
  this value as `RELEVANCE_THRESHOLD` in `src/rule_based_evaluator.py`.
- Use the same version of
  `data/reference/trusted_ecommerce_domains.csv` for every Rule-Based run.
- Reuse shared human labels across methods when the product, keyword, domain,
  and URL are the same.

The fixed 100-product keyword file is still pending. Final comparison runs
must not begin until that file is complete and the exact keyword for each
evaluation product has been frozen.

Validate every experiment result JSON:

```powershell
.\.venv\Scripts\python.exe src\evaluation\result_validator.py
```

Validate the ground-truth CSV:

```powershell
.\.venv\Scripts\python.exe src\evaluation\ground_truth.py
```

Calculate current metrics:

```powershell
.\.venv\Scripts\python.exe src\evaluation\metrics.py
```

The 15 shared human-confirmed label records cover all 20 currently stored
search results. The preliminary overall accuracy is `0.95`; Selenium +
Rule-Based is `1.0`, and the fake-provider Selenium + NanoLLM sample is `0.8`.
The labels were initially prepared with AI assistance and were then manually
checked by a project member. These values describe only the small committed
sample, not the final 100-product experiment. The current human-confirmed
sample contains no irrelevant results, so it is not a balanced final accuracy
dataset. The NanoLLM sample uses the fake provider, so its `0.0` estimated
cost must not be interpreted as a measured real-provider API cost.

## Progress checklist

This checklist describes the actual state of the
`feature/evaluation-metrics` branch. A checked item is implemented and
verified in the repository. An unchecked item is either incomplete or has not
yet been verified with a real external provider.

### Data and Selenium + Rule-Based work

- [x] Prepare a raw dataset containing 100 smartphone products.
- [x] Implement `src/data_processor.py`.
- [x] Validate the schema, missing values, duplicates, and numeric ranges.
- [x] Produce `processed_products.csv`, `processed_products.json`, and
  `validation_issues.csv`.
- [x] Implement and run the dataset-level `src/quality_check.py`.
- [x] Add a unique product-specific HTTPS reference URL to all 100 dataset
  rows and preserve it in the processed CSV/JSON outputs.
- [x] Implement `src/selenium_collector.py` and complete the initial Selenium
  connection test.
- [x] Add `data/reference/trusted_ecommerce_domains.csv`.
- [x] Implement `src/rule_based_evaluator.py`.
- [x] Implement the single-product `src/run_selenium_rule_based.py` pipeline.
- [x] Store standardized result JSON files with runtime and estimated-cost
  fields.

### Keyword and NanoLLM work

- [x] Add the initial LLM project structure and `.env.example`.
- [x] Implement structured keyword-generation and validation code.
- [x] Read products from `processed_products.json`.
- [x] Add OpenRouter client support without committing an API key.
- [x] Implement `src/keyword_loader.py`.
- [x] Implement `src/run_rule_based_batch.py`.
- [x] Add the `domain_ground_truth.csv` labeling schema.
- [x] Implement `src/nano_llm_evaluator.py`.
- [x] Implement `src/run_selenium_nano_llm.py`.
- [x] Verify the NanoLLM pipeline with a deterministic fake provider.
- [ ] Generate and verify 2-3 keywords using the real OpenRouter provider.
  The current three records were generated with the fake provider.
- [ ] Produce the fixed keyword list for all 100 products. The current
  `generated_keywords.json` contains only three records.
- [ ] Run and verify the real NanoLLM provider.
- [ ] Produce real-provider `predicted_relevant` and `relevance_score` values.
- [ ] Record measured model, prompt, API runtime, and API cost information.
- [ ] Produce a Selenium + NanoLLM result using the real provider. The current
  sample uses the fake provider.

### Review and evaluation work

- [x] Fetch and inspect the teammate's feature branch.
- [x] Validate the generated-keyword and ground-truth schemas.
- [x] Test the keyword loader with three records.
- [x] Review the Rule-Based batch runner and branch diff.
- [x] Validate all current result JSON files against the shared schema.
- [x] Run the complete API-free unit-test suite.
- [x] Implement runtime, estimated-cost, relevance-ratio, and accuracy metric
  calculations.
- [x] Add ground-truth loading and validation.
- [x] Select a 10-product evaluation subset containing 10 different brands.
- [x] Add 15 shared relevance labels covering all 20 current result
  rows and calculate the preliminary accuracy metrics.
- [x] Have a project member manually confirm the shared labels before using
  them as human ground truth.
- [x] Document the human relevance rule, 10-product subset, `max_results = 5`,
  Rule-Based threshold `0.60`, and shared trusted-domain list.
- [ ] Freeze one exact keyword per evaluation product and use it unchanged
  across all four methods.
- [ ] Re-run a small live Rule-Based batch with two or three keywords if a
  fresh live-search verification is required.
- [ ] Merge the reviewed feature work into `main`. The evaluation work remains
  on `feature/evaluation-metrics`, while `main` still points to the earlier
  Selenium + Rule-Based commit.

### Planned next steps

- [ ] Add the Tavily API integration and Tavily + NanoLLM runner.
- [ ] Add the Agentic web-search approach and runner.
- [ ] Preserve the shared JSON output format across all four methods.
- [ ] Prepare the LangGraph node and workflow design.
- [ ] Run every method with the same fixed keyword list and comparison rules.
