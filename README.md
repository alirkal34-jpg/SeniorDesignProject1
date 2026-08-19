# SeniorDesignProject1

## Interactive presentation dashboard

The project includes a local, presentation-focused web dashboard that runs the
existing Python pipeline through an allowlisted set of actions. It displays
live console output and lets the presenter inspect generated CSV, JSON and
Markdown artifacts without typing each command manually. API keys remain in
the local `.env` file and are never returned to the browser.

Start the dashboard from the project root:

```powershell
.\.venv\Scripts\python.exe demo_dashboard.py
```

The browser opens at `http://127.0.0.1:8765`. Safe deterministic steps can be
run as a sequence. The live Task 1 LangGraph action loads one product, generates
a keyword with OpenRouter, sends it through all four real methods, ranks the
results, and stores both standardized method JSON files and a complete workflow
record. Live OpenRouter, Tavily and Selenium actions require explicit
confirmation.

## Category expansion (18-08-2026)

The project advisor asked us to stop validating the pipeline on smartphones
alone. Running a single category cannot show that the system generalizes
across different search intents and product structures, so the pipeline was
revised to cover ten e-commerce category groups with about fifty products
each:

| Category group | ID prefix | Products |
|---|---|---:|
| Elektronik, Cep Telefonu | `ELK` | 50 |
| Ev, Yaşam, Ofis, Kırtasiye | `EVY` | 50 |
| Anne, Bebek, Oyuncak | `ABO` | 50 |
| Saat, Moda, Takı, Ayakkabı | `SMT` | 50 |
| Kitap, Müzik, Hobi | `KMH` | 50 |
| Spor, Outdoor | `SPO` | 50 |
| Sağlık, Bakım, Kozmetik | `SBK` | 50 |
| Oto, Bahçe, Yapı Market | `OBY` | 50 |
| Petshop | `PET` | 50 |
| Süpermarket | `SPM` | 50 |

`data/reference/product_categories.csv` is the single source of truth for this
taxonomy. Every module reads it, so adding or resizing a category needs no
code change.

### What the revision changed

- **Product schema.** The smartphone schema made `storage_gb`, `ram_gb`,
  `display_size_inch`, `battery_mah` and `operating_system` mandatory, so a
  book or a detergent could never pass validation. The multi-category schema
  keeps a small mandatory core (`product_id`, `product_name`, `brand`,
  `category`, `category_group`, `source_url`) and moves everything else into an
  `attributes` JSON column, validated per category group.
- **`variant_label`.** Every category supplies this one attribute. It is the
  distinguishing spec that also becomes part of the search keyword: `256 GB`,
  `500 ml`, `42 Numara`, `1.5 kg`, `Ciltli`.
- **Trusted domains.** The reference table grew from 17 electronics sellers to
  44 domains covering all ten groups, including Kitapyurdu, Migros, Gratis,
  Boyner, ebebek, Koçtaş, Petlebi and Decathlon.
- **Keyword generation** now builds the keyword from `variant_label` instead of
  the smartphone-only `storage_gb` field.
- **Quality gate.** `quality_check.py` no longer hard-codes 100 rows and
  `P001`-`P100`; expected identifiers and per-category counts come from the
  taxonomy, and each group's product count is reported.

The original 100-smartphone dataset, its committed results, and the frozen
evaluation report are untouched. They remain reproducible as the prior
baseline, and the smartphone processing path is byte-identical.

### Measuring accuracy on a labeled subset

Running 500 products through 4 methods with 5 results each produces roughly
10,000 result rows, which cannot be labeled by hand. The two measurements are
therefore separated:

- **All 500 products** are run to compare runtime, cost, and relevant-result
  ratio per method and per category. These need no human labels.
- **A 20-product labeled subset** (2 products from each category group,
  `data/evaluation/evaluation_subset_multicategory.csv`) carries the human
  relevance labels used for accuracy. Every category is represented, and the
  two products in each category come from different brands.

### Dataset provenance

`src/product_scraper.py` implements the acquisition path with BeautifulSoup4
and Selenium. The committed dataset was collected from **Akakçe on
18-08-2026**: 489 products, `acquisition_mode: scraped`, every row carrying the
listing's own HTTPS product URL.

An offline provider generates a **synthetic** dataset of the same shape for
tests and demonstrations. Whichever dataset is present, its metadata records
which path produced it, a synthetic one carries an explicit warning, and unit
tests assert that the declaration cannot silently disappear. Resuming refuses
to mix the two.

Collected products per category group:

| Category group | Products |
|---|---:|
| Elektronik, Cep Telefonu | 50 |
| Ev, Yaşam, Ofis, Kırtasiye | 50 |
| Anne, Bebek, Oyuncak | 50 |
| Saat, Moda, Takı, Ayakkabı | **39** |
| Kitap, Müzik, Hobi | 50 |
| Spor, Outdoor | 50 |
| Sağlık, Bakım, Kozmetik | 50 |
| Oto, Bahçe, Yapı Market | 50 |
| Petshop | 50 |
| Süpermarket | 50 |
| **Total** | **489** |

### What the real data showed

Two findings came out of collecting real listings rather than generating them,
and both are results in their own right.

**Commercial sites actively prevent automated collection.** Cimri serves a
Cloudflare block page to any automated request. Akakçe answers normally but
rate-limits: after roughly six rapid requests it returns a
"Güvenlik doğrulaması" interstitial. Waiting 20 seconds between requests avoids
it entirely. No bypass is implemented; the scraper recognises the interstitial,
backs off, and reports it.

**Attribute richness differs structurally by category.** The taxonomy first
required category-specific attributes such as `ram_gb`, `creator`, `age_range`
and `discipline`. Measured against real listings, **not one of them appeared in
a single title**. Listing pages publish a title and a price, not a spec sheet.
The contract was therefore rebuilt around what the source actually states:
`variant_label` is required, and category-specific attributes are optional and
range-checked when present.

How often a title states a usable specification varies widely:

| Category group | Titles with a usable variant |
|---|---|
| Elektronik, Kozmetik, Petshop, Süpermarket | ~100% (GB, ml, kg, g) |
| Kitap, Anne-Bebek, Oto | 80-95% |
| Spor, Outdoor | ~84% (dimensions such as `200x200x145`) |
| Ev, Yaşam | ~66% |
| Saat, Moda, Takı, Ayakkabı | ~34% |

Fashion is the reason one category holds 39 products instead of 50: Akakçe does
not list fifty watches, shoes or bags whose titles state a specification. This
is a property of the market data, not a pipeline limitation, and it is exactly
the kind of cross-category variation the revision set out to expose.

To recover a variant the parser reads, in order of preference, a number with a
unit (`256 GB`), a dimension (`200x200x145`), or a manufacturer model code
(`GA-2100-1A1DR`). Products whose title yields none of these are skipped during
collection, so every row in the dataset satisfies the contract: the processed
dataset has **489 valid rows and zero invalid rows**.

## Current progress (31-07-2026)

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
- A completed live evaluation on the fixed 10-product subset across all four
  methods (40 experiments and 199 result rows).
- 107 shared ground-truth records: 21 previously verified records plus 86
  final-evaluation URLs individually reviewed by the project owner. The 35
  question-marked decisions were adjudicated consistently against the frozen
  relevance rule and retain an audit trail.
- A final metrics report with 100% ground-truth coverage for the selected live
  evaluation run.
- A human-readable four-method comparison report generated from the final
  metrics JSON.
- An end-to-end LangGraph that loads processed product data, generates one
  structured keyword, sends it unchanged through all four methods, ranks the
  results, and persists the complete workflow record.
- A retained single-product live LangGraph execution using OpenRouter, Tavily,
  Selenium/Bing, and all four comparison methods.

All four methods now have retained live smoke-test evidence and a completed
10-product live comparison. The first
Selenium + NanoLLM attempt was blocked by Google's CAPTCHA page, so the
successful run used Bing through the same Selenium collector. The committed
fake outputs must not be presented as measured real-provider results.

## Project structure

```text
first-task/
|-- data/
|   |-- raw/                         # 100 smartphones + 500 multi-category products
|   |-- processed/                   # Processed products and fixed keywords
|   |-- evaluation/                  # 10-smartphone and 20-product subsets
|   |-- labels/                      # Human relevance ground truth
|   `-- reference/
|       |-- product_categories.csv   # The ten-category taxonomy
|       `-- trusted_ecommerce_domains.csv
|-- results/
|   |-- selenium_rule_based/
|   |-- selenium_nano_llm/
|   |-- tavily_llm/
|   `-- agentic_search/
|-- src/
|   |-- evaluation/
|   |   |-- final_metrics.py
|   |   |-- final_report.py
|   |   |-- ground_truth.py
|   |   |-- metrics.py
|   |   `-- result_validator.py
|   |-- category_taxonomy.py         # Loads the category reference file
|   |-- product_catalog.py           # Deterministic offline product catalog
|   |-- product_scraper.py           # BeautifulSoup4 + Selenium acquisition
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

## Multi-category pipeline

Inspect the taxonomy:

```powershell
.\.venv\Scripts\python.exe src\category_taxonomy.py
```

Process and quality-check the collected dataset. The gate is run at the floor
the source can actually fill; its report still lists every category against the
taxonomy target, so a shortfall stays visible:

```powershell
.\.venv\Scripts\python.exe src\data_processor.py --dataset multicategory
.\.venv\Scripts\python.exe src\quality_check.py --dataset multicategory --min-per-category 39
```

Rebuild an equivalent dataset offline, without touching the network:

```powershell
.\.venv\Scripts\python.exe src\product_scraper.py --provider offline
```

Recompute the attributes column after improving the title parser, without
scraping again:

```powershell
.\.venv\Scripts\python.exe src\product_scraper.py --rederive-attributes
```

Collect real listings instead of the synthetic snapshot. Chrome is required,
and the run stops with a clear error if the listing markup changed or the
request was blocked. No CAPTCHA bypass is implemented:

```powershell
.\.venv\Scripts\python.exe src\product_scraper.py --provider selenium --site akakce
```

Add `--debug-html tmp\scraped_pages` to save every received page, which tells a
markup change apart from a blocked request.

Site status, measured on 18-08-2026:

| Site | Status |
|---|---|
| `akakce` | Works, with rate limiting. Product cards are `li.w`, the brand is in the `data-mk` attribute, one search returns about 32 products. Cloudflare starts serving a "Güvenlik doğrulaması" interstitial after roughly six rapid requests. Default. |
| `cimri` | Blocked outright. Serves a Cloudflare "you have been blocked" page to automated requests. The adapter is kept so the error message can say so instead of blaming the selectors. |
| `hepsiburada`, `trendyol` | Adapters written from public markup, not verified against a live run. |

### Bot protection is respected, not bypassed

Both price-comparison sites protect themselves with Cloudflare. This project
does not work around that: there is no stealth driver, no user-agent spoofing
and no challenge solving. The scraper instead

- waits `--delay` seconds between requests (8 by default),
- recognises the interstitial by its wording and backs off before retrying,
- stops after a few refusals and reports the rate limit plainly,
- keeps everything collected so far.

Because of this, the dataset is normally finished over several sessions:

```powershell
.\.venv\Scripts\python.exe src\product_scraper.py --provider selenium --site akakce --resume
```

`--resume` keeps categories that already reached the target and only requests
the missing ones. A rate-limited run still saves its progress and exits with a
non-zero status, so nothing collected is thrown away.

The first live session on 18-08-2026 completed three category groups
(150 products) before the interstitial appeared.

Resuming will not mix provenance. If the existing dataset was produced offline
and the new run scrapes, or the other way round, the run stops rather than
labeling generated rows as measured ones. Move the old dataset aside first. The
metadata also separates `collected_this_run` from
`carried_over_from_previous_run`, so a resumed run cannot look like a fresh
collection.

Because one listing page holds about 32 products and the search pages expose no
pagination, each category is filled from four search terms defined in
`SEARCH_TERMS`, merged and deduplicated. This also gives better within-category
variety than a single query would. The run prints how many products each term
contributed, so a term that stops working is visible immediately.

Every category is attempted before any shortfall is reported, so one run shows
the state of all ten groups. Lower the bar with `--min-per-category 40` when a
category is genuinely thin on the site.

Scraped listings only carry what the title states. `variant_label` is parsed
out of the title (`iPhone 17 256 GB Siyah` gives `256 GB`), and the numeric
attributes a category needs are derived from it where possible. Attributes a
listing page does not expose are left empty on purpose, so the validation
report shows how complete the scraped data really is.

Generate the fixed keyword for every multi-category product:

```powershell
.\.venv\Scripts\python.exe src\keyword_generator.py --provider fake --limit 489 --input data\processed\processed_products_multicategory.json --output data\processed\generated_keywords_multicategory.json
```

Run the 20-product labeled subset through all four methods without network
calls:

```powershell
.\.venv\Scripts\python.exe src\run_evaluation_batch.py --subset data\evaluation\evaluation_subset_multicategory.csv --keywords data\processed\generated_keywords_multicategory.json --limit 20 --execution-mode fake
```

Run one multi-category product through the complete Task 1 LangGraph:

```powershell
.\.venv\Scripts\python.exe src\langgraph_flow.py --flow end-to-end --product-id ELK001 --products data\processed\processed_products_multicategory.json --keyword-provider fake --execution-mode fake
```

Save live multi-category results outside the frozen smartphone baseline. New
experiments must always use `--results-directory`, because `results/` holds the
committed evaluation that the final report was built from:

```powershell
.\.venv\Scripts\python.exe src\run_evaluation_batch.py --subset data\evaluation\evaluation_subset_multicategory.csv --keywords data\processed\generated_keywords_multicategory.json --limit 20 --execution-mode live --save --allow-live-batch --results-directory results_multicategory
```

The OpenRouter free tier allows 50 model requests per day per key, and one full
20-product run needs about 80 (one per product for Selenium + NanoLLM and for
Tavily + NanoLLM, two per product for Agentic Search, which also plans its
queries with the model).

Two ways to get past that limit are supported. Configure additional keys as
`OPENROUTER_API_KEY_2`, `_3` and so on: each OpenRouter account carries its own
daily allowance, and the client moves to the next key when one is spent, so two
keys give 100 requests a day. A key stopped by a *daily* limit is set aside for
the rest of the run, while a transient per-minute limit is still handled by
backing off.

Alternatively, continue a stopped batch in the next session without spending
quota on work that already finished:

```powershell
.\.venv\Scripts\python.exe src\run_evaluation_batch.py --subset data\evaluation\evaluation_subset_multicategory.csv --keywords data\processed\generated_keywords_multicategory.json --limit 20 --execution-mode live --save --allow-live-batch --results-directory results_multicategory --skip-existing
```

`--skip-existing` reads the result files already in the directory and runs only
the missing product/method pairs.

Export the returned URLs to an Excel workbook for human relevance review, then
import the completed workbook as ground truth:

```powershell
.\.venv\Scripts\python.exe src\evaluation\export_label_workbook.py results_multicategory
.\.venv\Scripts\python.exe src\evaluation\import_label_workbook.py
```

The workbook deliberately omits every method's prediction. Showing a method's
guess to the person labeling the data biases the ground truth toward that
method and inflates its measured accuracy. Each URL is labeled once and the
label is shared by every method that returned it, so the four methods are
always scored against identical ground truth.

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
Agentic Search, and result aggregation nodes. The complete Task 1 graph adds
product loading, structured keyword generation, per-method result ranking,
runtime/cost aggregation, and persistent workflow evidence.

Run the compiled four-method comparison graph without network calls:

```powershell
.\.venv\Scripts\python.exe src\langgraph_flow.py --flow comparison --execution-mode fake
```

Run the complete product-data -> keyword -> four-method LangGraph without
network calls:

```powershell
.\.venv\Scripts\python.exe src\langgraph_flow.py --flow end-to-end --product-id P001 --keyword-provider fake --execution-mode fake
```

Run and save one complete live Task 1 LangGraph execution:

```powershell
.\.venv\Scripts\python.exe src\langgraph_flow.py --flow end-to-end --product-id P001 --keyword-provider openrouter --execution-mode live --max-results 5 --save
```

The live command saves four standardized method payloads beneath
`reports/langgraph_runs/method_results/` and the complete
product-to-ranked-results workflow record beneath `reports/langgraph_runs/`.
This keeps new demonstration runs separate from the frozen evaluation baseline
under `results/`.

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

The ground-truth file contains 107 shared labels. The project owner opened and
reviewed all 86 final-evaluation URLs one by one on 31 July 2026. Of these, 51
received an exact TRUE/FALSE decision directly and 35 were marked with a
question mark; the latter were resolved consistently against the frozen rule.
`data/labels/final_evaluation_human_labels.csv` preserves the original human
decision, human note, final label, adjudication basis, and provenance.

`reports/final_evaluation_metrics.json` selects the latest retained live result
for every method/product pair in the fixed 10-product subset. This gives 40
experiments and 199 result rows with 100% ground-truth coverage.

| Method | Accuracy | Average runtime | Relevant-result ratio | Estimated cost |
|---|---:|---:|---:|---:|
| Agentic Search | 66.00% | 24.730 s | 100.00% | $0.00 |
| Selenium + NanoLLM | 66.00% | 15.986 s | 98.00% | $0.00 |
| Selenium + Rule-Based | 69.39% | 5.455 s | 83.67% | $0.00 |
| Tavily + NanoLLM | 74.00% | 8.622 s | 82.00% | $0.00 |

Overall accuracy is 68.84% (137 correct predictions out of 199 labeled
results). The retained runs record zero estimated cost because the configured
OpenRouter model was free and `TAVILY_COST_PER_SEARCH_USD` was set to zero;
this is experiment metadata, not a general claim that the providers are always
free.

The matching human-readable deliverable is
`reports/final_evaluation_report.md`. Regenerate it after any metrics change:

```powershell
.\.venv\Scripts\python.exe src\evaluation\final_metrics.py
.\.venv\Scripts\python.exe src\evaluation\final_report.py
```

## Validation, metrics, and tests

```powershell
.\.venv\Scripts\python.exe src\evaluation\result_validator.py results
.\.venv\Scripts\python.exe src\evaluation\ground_truth.py
.\.venv\Scripts\python.exe src\evaluation\metrics.py
.\.venv\Scripts\python.exe src\evaluation\final_metrics.py
.\.venv\Scripts\python.exe src\evaluation\final_report.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test*.py" -v
```

The metrics module reports valid/invalid result-file counts, invalid-file
details, method-level experiment/result counts, relevant-result ratio, average
runtime, total/average estimated cost, ground-truth coverage, confusion counts,
and accuracy.

### Behavior-locking tests

Three test files record how the pipeline behaves today rather than how it
should behave. They were written before the category expansion so that any
change in the cleaning, scoring or orchestration logic would surface as a
failing test instead of a silent drift:

```text
tests/test_baseline_data_contract.py           # schema, cleaning, validation codes
tests/test_baseline_method_contract.py         # domain table, scoring, keywords, URLs
tests/test_baseline_orchestration_contract.py  # graph topology and result contract
```

When the expansion deliberately changed a locked behavior, the test was
updated and the reason recorded in a `CHANGED` comment next to the assertion.
Three behaviors changed this way: the trusted-domain table, the deterministic
NanoLLM domain list, and the workflow state, which now also carries
`category_group` and `attributes`.

`tests/test_multicategory_pipeline.py` covers the taxonomy, the offline
catalog, the BeautifulSoup4 listing parser, category-aware attribute
validation, the committed snapshot, and the labeled subset.

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
- [x] Metrics, evaluation subset, ground-truth loading, and 107 shared labels.
- [x] Three-product real OpenRouter keyword smoke test and retained metadata.
- [x] One-product live Tavily + NanoLLM experiment.
- [x] One-product live LLM-planned Agentic Search experiment.
- [x] One-product live Selenium + NanoLLM experiment using Selenium with Bing.
- [x] Fixed free OpenRouter model for reproducible structured output.
- [x] Live provider/model/prompt/runtime/cost fields retained in result files.
- [x] All four methods run live on the fixed 10-product evaluation subset.
- [x] Final live metrics report with 100% label coverage.
- [x] Individual human review of all 86 final-evaluation URLs, with documented
  adjudication for 35 question-marked decisions.
- [x] Human-readable runtime/cost/accuracy comparison report.
- [x] Product-data-to-keyword-to-four-method end-to-end LangGraph.
- [x] One-product live end-to-end LangGraph run with four saved method payloads,
  per-method rankings, runtime/cost aggregation, and workflow evidence.

### Completed for the ten-category revision

- [x] Ten-category taxonomy reference read by every module.
- [x] Category-agnostic product schema with a per-category `attributes` column.
- [x] BeautifulSoup4 + Selenium scraper with per-site listing adapters.
- [x] 489 products scraped from Akakçe, 9 of 10 groups at the 50-product
  target, with provenance metadata and resumable, rate-limit-aware collection.
- [x] Category-aware DataProcessor validation: 489 valid rows, 0 invalid.
- [x] Taxonomy-driven quality gate with per-category coverage reporting and a
  configurable floor.
- [x] Trusted-domain table expanded from 17 to 44 domains across all groups.
- [x] Keyword generation driven by `variant_label` for every category.
- [x] 20-product labeled evaluation subset, 2 per category, distinct brands.
- [x] Excel export/import tooling for human relevance review.
- [x] Behavior-locking test suite; test count grew from 79 to 265.
- [x] The frozen smartphone dataset, results and report stay reproducible.

### Requires local API keys or manual work

- [ ] Collect human relevance labels for the 20-product multi-category subset
  so accuracy can be reported per category group.
- [ ] Run the full 489-product dataset live to compare runtime, cost, and
  relevant-result ratio per method and per category.
- [ ] Decide whether the fashion group stays at 39 products or is topped up
  from a second listing site.
- [ ] Generate all 100 fixed keywords with the real provider if the final
  experiment requires LLM-generated rather than deterministic keywords.
- [ ] Repeat the live comparison if confidence intervals or run-to-run
  variance are required for the final report.
