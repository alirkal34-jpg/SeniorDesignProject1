# From-Scratch Live Run

15 products, 3 categories (phone, cat food, biscuit).

---

## Setup

```powershell
$env:NANO_LLM_MODEL = "google/gemma-4-26b-a4b-it"
$env:AGENTIC_PLANNER_MODEL = "google/gemma-4-26b-a4b-it"
```

Check: `echo $env:NANO_LLM_MODEL` has no `:free` suffix.

```powershell
Remove-Item -Recurse -Force tmp\canli -ErrorAction SilentlyContinue
```

---

### 1. Scrape — live, from Akakçe

```powershell
.\.venv\Scripts\python.exe src\product_scraper.py --provider selenium --site akakce --categories elektronik_cep_telefonu,petshop,supermarket --limit-per-category 5 --min-per-category 5 --delay 3 --output tmp\canli\raw.csv
```

Check: ~31s, 15 products, 3/3 categories collected.

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\raw.metadata.json
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\raw.csv --limit 3
```

Check: `"acquisition_mode": "scraped"`, each row has its own product URL.

### 2. Process

```powershell
.\.venv\Scripts\python.exe src\data_processor.py --dataset multicategory --input tmp\canli\raw.csv --output-directory tmp\canli
```

Check: `Valid products: 15, Invalid products: 0`

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\validation_issues_multicategory.csv --limit 5
```

Check: empty — zero problem rows.

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\processed_products_multicategory.csv --limit 15 --fields product_id,category_group,attributes
```

Check: phone has `storage_gb`, cat food has `weight_kg`+`animal_type`, biscuit has `net_weight_g` — all three have `variant_label`.

### 3. Quality gate

```powershell
.\.venv\Scripts\python.exe src\quality_check.py --dataset multicategory --input tmp\canli\processed_products_multicategory.csv --categories elektronik_cep_telefonu,petshop,supermarket --min-per-category 5
```

Check: `Dataset-level quality check: PASSED`.

### 4. Keyword generation

```powershell
.\.venv\Scripts\python.exe src\keyword_generator.py --input tmp\canli\processed_products_multicategory.json --limit 15 --output tmp\canli\keywords.json --provider fake
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\keywords.json --limit 5
```

Produces: 15 deterministic keywords, one per product.

Compare against the live model, first 5 products (~8s):

```powershell
.\.venv\Scripts\python.exe src\keyword_generator.py --input tmp\canli\processed_products_multicategory.json --limit 5 --output tmp\canli\keywords_live.json --provider openrouter
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\keywords_live.json --limit 5
```

Check: does the live model drop a distinguishing word (color, flavor, "spayed")?

### 5. Four methods — search + relevance judgment (3 products, live)

```powershell
.\.venv\Scripts\python.exe src\run_evaluation_batch.py --subset tmp\canli\processed_products_multicategory.json --keywords tmp\canli\keywords.json --execution-mode live --limit 3 --max-results 5 --save --results-directory tmp\canli\results --skip-existing
```

Check: ~113s, 12 runs, `failed_count: 0`. Chrome opens and searches Bing.

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\results\selenium_rule_based --limit 1 --fields product_id,keyword,method,model,prompt_version,runtime_seconds,estimated_cost_usd
```

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py tmp\canli\results\tavily_llm --limit 1 --fields product_id,method,model,results
```

Check: rule-based method's `prompt_version` is `not_applicable` — no LLM, this is the control group.

```powershell
.\.venv\Scripts\python.exe src\evaluation\result_validator.py tmp\canli\results
```

Check: `Valid files: 12 / Invalid files: 0`.

> **All 15 products** (run BEFORE the presentation, ~12.7 min):
> ```powershell
> .\.venv\Scripts\python.exe src\run_evaluation_batch.py --subset tmp\canli\processed_products_multicategory.json --keywords tmp\canli\keywords.json --execution-mode live --limit 15 --allow-live-batch --max-results 5 --save --results-directory tmp\canli\results --skip-existing
> ```
> Rerun the same command live during the presentation — `--skip-existing` returns in seconds.

### 6. This run's own finding

```powershell
.\.venv\Scripts\python.exe -c "import json,glob,collections;s=collections.defaultdict(lambda:[0,0]);[ (s[d['method']].__setitem__(1,s[d['method']][1]+len(d['results'])), s[d['method']].__setitem__(0,s[d['method']][0]+sum(1 for r in d['results'] if r['predicted_relevant']))) for d in (json.load(open(f,encoding='utf-8')) for f in glob.glob('tmp/canli/results/*/*.json'))];[print('%-22s %3d/%3d  %%%.1f'%(m,v[0],v[1],100*v[0]/v[1])) for m,v in sorted(s.items())]"
```

Check (with all 15 products): both LLM-based methods say "relevant" to ~100% of results — the same pattern behind Finding 2 (specificity 0.000 → 0.846 after prompt alignment). The control group (`selenium_rule_based`) is unaffected.

### 7. Why labeling isn't done live

```powershell
.\.venv\Scripts\python.exe src\evaluation\export_label_workbook.py tmp\canli\results --subset tmp\canli\processed_products_multicategory.json --output tmp\canli\label_workbook.xlsx
```

Produces: Excel workbook — no prediction columns, so the reviewer's answer can't be biased by a method's guess.

```powershell
.\.venv\Scripts\python.exe src\evaluation\show.py reports_multicategory\multicategory_evaluation_metrics.json --fields product_count,experiment_count,result_count,labeled_result_count,ground_truth_coverage_ratio,accuracy
```

Check: 20 products, 80 runs, 399/399 labeled, coverage 1.0, accuracy 0.7619 — the real reported numbers.

### 8. Cleanup

```powershell
git status
```

Check: `tmp/` is gitignored, nothing to commit.

---

Note: the full-15-product command in step 5 was corrected — the original `DEMO_sifirdan_kosum.md` had it split mid-word across lines and it would not run as pasted.
