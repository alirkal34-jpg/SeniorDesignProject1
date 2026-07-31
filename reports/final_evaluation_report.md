# Final Four-Method Evaluation Report

## Objective

This report compares four approaches for finding transactional e-commerce pages from fixed smartphone keywords.
It is the human-readable companion to `final_evaluation_metrics.json`.

## Experimental protocol

- Products: 10 fixed smartphones.
- Input: one fixed keyword per product, reused unchanged by every method.
- Maximum search results: 5 per product and method.
- Rule-Based relevance threshold: 0.60.
- Experiments: 40 live method/product runs.
- Evaluated results: 199.
- Ground-truth records available: 107.
- Final-run label coverage: 100.00%.
- Relevance rule: correct model and capacity in a transactional page; wrong model/capacity, accessories, news, and reviews are irrelevant.

## Results

| Method | Runs | Results | Accuracy | Avg. runtime | Relevant ratio | Total estimated cost |
|---|---:|---:|---:|---:|---:|---:|
| Agentic Search | 10 | 50 | 66.00% | 24.730 s | 100.00% | $0.00000000 |
| Selenium + NanoLLM | 10 | 50 | 68.00% | 15.986 s | 98.00% | $0.00000000 |
| Selenium + Rule-Based | 10 | 49 | 65.31% | 5.455 s | 83.67% | $0.00000000 |
| Tavily + NanoLLM | 10 | 50 | 72.00% | 8.622 s | 82.00% | $0.00000000 |

Overall accuracy was **67.84%** (135 correct predictions out of 199 labeled results). The aggregate
confusion counts were:

- True positives: 124
- True negatives: 11
- False positives: 57
- False negatives: 7

## Interpretation

- Highest measured accuracy: **Tavily + NanoLLM** at 72.00%.
- Lowest average runtime: **Selenium + Rule-Based** at 5.455 seconds.
- Agentic Search marked every returned result relevant, which produced high recall behavior but also the largest false-positive tendency.
- Relevant-result ratio is not accuracy; it only describes how often a method predicted relevance.

## Cost interpretation

Every retained run reports an estimated cost of $0.00 because the configured OpenRouter model was free and Tavily search cost was recorded as zero for this experiment.
This does not mean the providers or future runs are always free.

## Limitations

- The 86 final-evaluation labels were AI-assisted and then explicitly accepted by the project owner; they were not independently entered one URL at a time.
- The fixed 100-keyword file is deterministic; a separate three-product live OpenRouter smoke output proves the real keyword API path.
- Selenium used Bing for the successful retained NanoLLM run after Google presented a CAPTCHA page.
- One run per product/method is reported, so variance and confidence intervals are outside this task's current scope.

## Reproduction

```powershell
.\.venv\Scripts\python.exe src\evaluation\final_report.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test*.py" -v
```
