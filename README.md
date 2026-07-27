# SeniorDesignProject1

## Current progress (28-07-2026)

This repository contains the data pipeline and the first comparison prototype
for four smartphone search-result evaluation methods.

Completed and locally verified:

- A raw and processed dataset containing 100 smartphone products.
- `DataProcessor` schema checks, cleaning, numeric conversion, missing-value
  checks, duplicate checks, numeric-range validation, and row-level
  `validation_status`/`validation_errors`.
- Dataset-level quality checks and a unique HTTPS reference URL for every
  product.
- Selenium search-result collection.
- Selenium + Rule-Based evaluation with a fixed `0.60` threshold.
- A fixed 100-product keyword list and provenance metadata.
- Keyword loading and batch Rule-Based execution.
- Selenium + NanoLLM, Tavily + NanoLLM, and Agentic Search runners with fake
  providers for repeatable API-free tests.
- OpenRouter keyword generation and relevance-evaluation clients.
- Tavily search integration.
- A successful three-product live OpenRouter keyword smoke test.
- Successful one-product live Selenium + NanoLLM, Tavily + NanoLLM, and Agentic
  Search smoke tests.
- An OpenRouter-based Agentic query planner that chooses search queries before
  the Selenium/Bing search tool is executed.
- A compiled Agentic LangGraph flow with `plan`, `search`, `evaluate`, and
  `aggregate` nodes.
- A compiled comparison LangGraph with shared input, four method nodes, result
  aggregation, and per-method error isolation.
- A shared result validator, human ground-truth loader, and metrics module.
- A fixed 10-product evaluation subset and 15 manually confirmed shared labels.

All four methods now have retained live smoke-test evidence. The first
Selenium + NanoLLM attempt was blocked by Google's CAPTCHA page, so the
successful run used Bing through the same Selenium collector. The committed
fake outputs must not be presented as measured real-provider results.

## Project structure

```text
first-task/
|-- data/
|   |-- raw/                         # Original 100-product dataset
|   |-- processed/                   # Processed products and fixed keywords
|   |-- evaluation/                  # Fixed 10-product evaluation subset
|   |-- labels/                      # Human relevance ground truth
|   `-- reference/
|       `-- trusted_ecommerce_domains.csv
|-- results/
|   |-- selenium_rule_based/
|   |-- selenium_nano_llm/
|   |-- tavily_llm/
|   `-- agentic_search/
|-- src/
|   |-- evaluation/
|   |   |-- ground_truth.py
|   |   |-- metrics.py
|   |   `-- result_validator.py
|   |-- data_processor.py
|   |-- quality_check.py
|   |-- selenium_collector.py
|   |-- rule_based_evaluator.py
|   |-- keyword_generator.py
|   |-- keyword_loader.py
|   |-- nano_llm_evaluator.py
|   |-- tavily_client.py
|   |-- agentic_search.py
|   |-- langgraph_flow.py
|   |-- run_selenium_rule_based.py
|   |-- run_rule_based_batch.py
|   |-- run_selenium_nano_llm.py
|   |-- run_tavily_llm.py
|   |-- run_agentic_search.py
|   `-- run_evaluation_batch.py
|-- tests/
|-- .env.example
|-- .gitignore
|-- README.md
`-- requirements.txt
```

## Installation

Python 3 and Google Chrome are required. In PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` only for real-provider runs:

```text
OPENROUTER_API_KEY=
NANO_LLM_MODEL=google/gemma-4-26b-a4b-it:free
AGENTIC_PLANNER_MODEL=google/gemma-4-26b-a4b-it:free
TAVILY_API_KEY=
TAVILY_COST_PER_SEARCH_USD=0
```

Never commit `.env`, API keys, tokens, or passwords.

The fixed `google/gemma-4-26b-a4b-it:free` model is used instead of the
random `openrouter/free` router so repeated experiments use the same model.

## Data processing

```powershell
.\.venv\Scripts\python.exe src\data_processor.py
.\.venv\Scripts\python.exe src\quality_check.py
.\.venv\Scripts\python.exe src\rule_based_evaluator.py
```

Generated data files:

```text
data/processed/processed_products.csv
data/processed/processed_products.json
data/processed/validation_issues.csv
```

## Fixed keyword list

`data/processed/generated_keywords.json` contains exactly one fixed keyword for
each product ID from `P001` through `P100`. The accompanying
`generated_keywords.metadata.json` records whether the list was produced with
the fake or live provider, plus model, prompt version, runtime, and estimated
cost.

The retained three-product OpenRouter smoke-test output is stored separately as
`generated_keywords.live_smoke.json` and
`generated_keywords.live_smoke.metadata.json`, so it does not overwrite the
fixed 100-product experiment input.

Generate an API-free deterministic list:

```powershell
.\.venv\Scripts\python.exe src\keyword_generator.py --provider fake --limit 100
```

Generate and verify three real OpenRouter keywords before attempting all 100:

```powershell
.\.venv\Scripts\python.exe src\keyword_generator.py --provider openrouter --limit 3
.\.venv\Scripts\python.exe src\keyword_generator.py --provider openrouter --limit 100
```

OpenRouter requests are processed in three-product batches. Validate the fixed
list without making an API call:

```powershell
.\.venv\Scripts\python.exe src\keyword_loader.py --limit 100
```

## Running the four methods

Selenium + Rule-Based:

```powershell
.\.venv\Scripts\python.exe src\run_selenium_rule_based.py --max-results 5
.\.venv\Scripts\python.exe src\run_rule_based_batch.py --limit 3 --max-results 5
```

Selenium + NanoLLM API-free:

```powershell
.\.venv\Scripts\python.exe src\run_selenium_nano_llm.py --search-provider fake --provider fake --max-results 5
```

Selenium + NanoLLM live:

```powershell
.\.venv\Scripts\python.exe src\run_selenium_nano_llm.py --search-provider selenium --search-engine bing --provider openrouter --max-results 5
```

Both Selenium runners support `--search-engine google` and
`--search-engine bing`. Bing is the default because the automated Google smoke
test reached Google's CAPTCHA page. No CAPTCHA bypass is implemented.

Tavily + NanoLLM API-free and live:

```powershell
.\.venv\Scripts\python.exe src\run_tavily_llm.py --search-provider fake --evaluator-provider fake --max-results 5
.\.venv\Scripts\python.exe src\run_tavily_llm.py --search-provider tavily --evaluator-provider openrouter --max-results 5
```

Agentic Search API-free and live:

```powershell
.\.venv\Scripts\python.exe src\run_agentic_search.py --planner-provider fake --search-provider fake --evaluator-provider fake --max-results 5
.\.venv\Scripts\python.exe src\run_agentic_search.py --planner-provider openrouter --search-provider selenium --search-engine bing --evaluator-provider openrouter --max-results 5
```

The live Agentic method uses an OpenRouter LLM to select one to three queries,
executes them using Selenium with Bing, deduplicates the search results, and
evaluates them with the NanoLLM provider. This keeps Agentic Search independent
from the separate Tavily + NanoLLM method. The older
`openrouter+tavily+openrouter` JSON is retained only as legacy smoke-test
evidence. `src/langgraph_flow.py` implements the current process as a compiled
four-node Agentic flow. It also provides a six-node comparison flow containing
shared input, Selenium + Rule-Based, Selenium + NanoLLM, Tavily + NanoLLM,
Agentic Search, and result aggregation nodes.

Run the compiled four-method comparison graph without network calls:

```powershell
.\.venv\Scripts\python.exe src\langgraph_flow.py --flow comparison --execution-mode fake
```

Verify that the same fixed keyword reaches all four methods without making
network calls:

```powershell
.\.venv\Scripts\python.exe src\run_evaluation_batch.py --execution-mode fake --limit 2
```

Live batches are limited to three products unless `--allow-live-batch` is
supplied explicitly after the smoke tests succeed.

## Shared result contract

Every newly generated experiment JSON contains:

- `product_id`, `keyword`, and `method`
- `execution_mode` (`fake` or `live`)
- `provider`, `model`, and `prompt_version`
- `runtime_seconds` and `estimated_cost_usd`
- At most five result objects containing domain, URL, title, snippet,
  `predicted_relevant`, and `relevance_score`

Each saved execution includes the mode plus a unique UTC/UUID run identifier in
its filename. Repeated runs therefore cannot overwrite another fake or live
result for the same product and keyword.

## Evaluation protocol

The following settings are frozen for comparisons:

- Use `data/evaluation/evaluation_subset.csv` containing 10 products from 10
  different brands.
- Use one fixed keyword per product and pass it unchanged to all four methods.
- Use `max_results = 5`.
- Use the Rule-Based relevance threshold `0.60`.
- Use the same `trusted_ecommerce_domains.csv`.

A result is relevant when it matches the phone model in the keyword and, when
specified, its storage capacity, and has a transactional purpose such as a
retailer page, marketplace listing, classified listing, or price-comparison
page. Wrong model/capacity, accessories, news, and reviews are irrelevant.
Being out of stock does not change the relevance label.

The 15 manually confirmed labels currently match 20 committed result rows.
Additional teammate result files are retained but are not silently treated as
human-labeled data; the metrics report therefore shows partial ground-truth
coverage until those new URLs are manually reviewed.

## Validation, metrics, and tests

```powershell
.\.venv\Scripts\python.exe src\evaluation\result_validator.py results
.\.venv\Scripts\python.exe src\evaluation\ground_truth.py
.\.venv\Scripts\python.exe src\evaluation\metrics.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test*.py" -v
```

The metrics module reports valid/invalid result-file counts, invalid-file
details, method-level experiment/result counts, relevant-result ratio, average
runtime, total/average estimated cost, ground-truth coverage, confusion counts,
and accuracy.

## Status checklist

### Completed

- [x] 100-product raw and processed datasets.
- [x] DataProcessor and dataset-level quality checks.
- [x] Selenium + Rule-Based prototype and batch runner.
- [x] Fixed 100-product keyword list with provenance metadata.
- [x] OpenRouter keyword and relevance client code.
- [x] Selenium + NanoLLM runner.
- [x] Tavily search integration and Tavily + NanoLLM runner.
- [x] LLM-planned Agentic Search runner.
- [x] Compiled Agentic LangGraph plan/search/evaluate/aggregate flow.
- [x] Compiled four-method comparison LangGraph with error isolation.
- [x] Collision-free result storage for repeated fake and live executions.
- [x] Batch continuation after an individual product fails.
- [x] Valid/invalid JSON counts in the metrics report.
- [x] Shared JSON schema including execution/provider/model/prompt/runtime/cost.
- [x] API-free tests for all four pipelines.
- [x] Metrics, evaluation subset, ground-truth loading, and preliminary labels.
- [x] Three-product real OpenRouter keyword smoke test and retained metadata.
- [x] One-product live Tavily + NanoLLM experiment.
- [x] One-product live LLM-planned Agentic Search experiment.
- [x] One-product live Selenium + NanoLLM experiment using Selenium with Bing.
- [x] Fixed free OpenRouter model for reproducible structured output.
- [x] Live provider/model/prompt/runtime/cost fields retained in result files.

### Requires local API keys or manual work

- [ ] Generate all 100 fixed keywords with the real provider if the final
  experiment requires LLM-generated rather than deterministic keywords.
- [ ] Manually label the additional retained search-result URLs.
- [ ] Run all four methods on the fixed 10-product subset.
- [ ] Review this integration branch and merge it into `main`.
