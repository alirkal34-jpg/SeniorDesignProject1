# Multi-Category Four-Method Evaluation Report

## Objective

The first evaluation of this project covered smartphones only. The advisor asked whether the pipeline generalizes to other search intents and product structures, so the same four methods were rerun over 20 products drawn from 10 category groups. This report is the human-readable companion to `multicategory_evaluation_metrics.json` and `multicategory_category_metrics.json`.

## Experimental protocol

- Products: 20, spread across 10 category groups (2 products per group, different brands).
- Input: one generated keyword per product, reused unchanged by every method.
- Maximum search results: 5 per product and method.
- Experiments: 80 live method/product runs, no failures.
- Evaluated results: 399.
- Human-labeled URLs: 193.
- Label coverage of the evaluated results: 100.00%.
- Relevance rule: the page must be the product named in the keyword, including the stated variant, and must have transactional purpose. Out of stock is still relevant; a different variant, an accessory, a category page, news, or a review is not.

## Results

| Method | Results | Accuracy | Always-relevant baseline | Balanced accuracy | Precision | Recall | Specificity | Avg. runtime |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Tavily + NanoLLM | 100 | 82.00% | 72.00% | 68.95% | 80.68% | 98.61% | 39.29% | 12.079 s |
| Agentic Search | 100 | 78.00% | 77.00% | 52.18% | 77.78% | 100.00% | 4.35% | 27.840 s |
| Selenium + NanoLLM | 100 | 74.00% | 74.00% | 50.00% | 74.00% | 100.00% | 0.00% | 14.200 s |
| Selenium + Rule-Based | 99 | 70.71% | 75.76% | 50.91% | 76.14% | 89.33% | 12.50% | 5.551 s |

Overall accuracy across all four methods was **76.19%** (304 correct out of 399 labeled results).

## How to read the accuracy column

The *always-relevant baseline* column is the accuracy a method would reach by answering "relevant" to every URL it returned. It is not a hypothetical: it is the share of that method's own results that the reviewers judged relevant.

Methods that beat that baseline, and by how much: Tavily + NanoLLM (+10.0 pp), Agentic Search (+1.0 pp). A method that does not beat it has an accuracy that reflects the difficulty of the URLs it happened to return, not an ability to reject one — and a margin of one point or two says almost the same thing.

Specificity makes the same point directly: it is the share of genuinely irrelevant URLs a method rejected.

- **Tavily + NanoLLM** said "relevant" to 88.00% of its results and rejected 39.29% of the irrelevant ones (11 of 28).
- **Agentic Search** said "relevant" to 99.00% of its results and rejected 4.35% of the irrelevant ones (1 of 23).
- **Selenium + NanoLLM** said "relevant" to 100.00% of its results and rejected 0.00% of the irrelevant ones (0 of 26).
- **Selenium + Rule-Based** said "relevant" to 88.89% of its results and rejected 12.50% of the irrelevant ones (3 of 24).

## Accuracy per category group

| Category group | Labeled | Relevant share | Tavily + NanoLLM | Agentic Search | Selenium + NanoLLM | Selenium + Rule-Based |
|---|---:|---:|---:|---:|---:|---:|
| anne_bebek_oyuncak | 40 | 82.50% | 80.00% | 90.00% | 80.00% | 70.00% |
| elektronik_cep_telefonu | 40 | 95.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| ev_yasam_ofis_kirtasiye | 40 | 77.50% | 70.00% | 90.00% | 80.00% | 80.00% |
| kitap_muzik_hobi | 40 | 95.00% | 100.00% | 100.00% | 100.00% | 80.00% |
| oto_bahce_yapi_market | 40 | 75.00% | 90.00% | 80.00% | 70.00% | 70.00% |
| petshop | 40 | 65.00% | 80.00% | 60.00% | 60.00% | 60.00% |
| saat_moda_taki_ayakkabi | 40 | 70.00% | 60.00% | 70.00% | 80.00% | 50.00% |
| saglik_bakim_kozmetik | 40 | 67.50% | 90.00% | 60.00% | 60.00% | 60.00% |
| spor_outdoor | 39 | 56.41% | 80.00% | 60.00% | 40.00% | 66.67% |
| supermarket | 40 | 62.50% | 70.00% | 70.00% | 70.00% | 70.00% |

## Was the phone category representative?

Averaged over the four methods, the phone category scored 100.00% while the other categories averaged 73.52%. The advisor's concern is therefore supported by the measurement: phones were the easiest category in the set, so a phone-only result overstates how well the pipeline works elsewhere.

## Comparison with the frozen phone experiment

| Experiment | Products | Labeled results | Overall accuracy |
|---|---:|---:|---:|
| Phones only (frozen) | 10 | 199 | 68.84% |
| Multi-category | 20 | 399 | 76.19% |

The two experiments use different products, keywords and labels, so the overall figures are not directly comparable. They are shown together only to record that the earlier result remains reproducible and untouched.

## Labeling protocol

- Every unique URL was reviewed once, by hand, and the label is shared by every method that returned that URL, so the four methods are scored against identical ground truth.
- The review workbook deliberately hides `predicted_relevant` and `relevance_score`. Showing a method's guess to the reviewer would bias the ground truth toward that method.
- Review ran over two sessions because a provider daily limit split the experiment; the second workbook excluded every URL the first one already covered.
- Rows the reviewer marked as unresolved were settled in `data/labels/multicategory_label_adjudications.csv` instead of by editing the workbook, so the human record is unchanged and each adjudicated label carries the rule that produced it in its `notes` field. An adjudication cannot overturn an answer the reviewer actually gave.

## Limitations

- One run per product and method, so variance and confidence intervals are out of scope.
- Two products per category group is enough to compare methods on the same footing, but too few to characterize a category.
- The relevant share of returned URLs is high in every category, which compresses the range accuracy can move in and is why specificity and balanced accuracy are reported next to it.
- Costs are reported as $0.00 because the configured OpenRouter model was free and Tavily search cost was recorded as zero. This does not mean future runs are free.

## Reproduction

```powershell
.\.venv\Scripts\python.exe src\evaluation\import_label_workbook.py --workbook data\labels\label_review_session1.xlsx data\labels\label_review_session2.xlsx --adjudication data\labels\multicategory_label_adjudications.csv --output data\labels\multicategory_ground_truth.csv
.\.venv\Scripts\python.exe src\evaluation\build_manifest.py
.\.venv\Scripts\python.exe src\evaluation\final_metrics.py --manifest data\evaluation\final_evaluation_manifest_multicategory.json --output reports_multicategory\multicategory_evaluation_metrics.json
.\.venv\Scripts\python.exe src\evaluation\category_metrics.py
.\.venv\Scripts\python.exe src\evaluation\multicategory_report.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test*.py"
```
