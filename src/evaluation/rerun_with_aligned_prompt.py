"""Re-judge the stored search results with a prompt that matches the label rule.

The reported runs asked the model a question the reviewers were never asked.
The production prompt (``relevance-v1``, written 2026-07-24) counts a category
page as relevant; the labeling rule handed to the reviewers (2026-08-18) counts
a category page that does not reach the product as irrelevant. The measured
specificity of 0.00 could therefore be a model limitation or an artifact of
that mismatch, and the existing numbers cannot tell the two apart.

This re-runs only the evaluator, over the results already stored on disk. No
new search happens, so the URLs stay identical and every human label remains
valid. The rule-based method uses no model and is copied through unchanged, so
all four methods stay comparable on the same products.

The prompt was written once from the workbook's instruction sheet and is not
tuned against the labels: adjusting it until the score improves would fit the
prompt to the test set and void the comparison this script exists to make.

Two practical details keep a long run moving. Calls are paced, because the
free tier throttles bursts and one 429 costs a full backoff, which is far more
than the pause it replaces. And the run is resumable: a product already
written is skipped, so a daily quota limit can split the work across days
without losing anything.

Usage:

    .venv\\Scripts\\python.exe src\\evaluation\\rerun_with_aligned_prompt.py
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "final_evaluation_manifest_multicategory.json"
)
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "results_multicategory_prompt_v2"
DEFAULT_PACING_SECONDS = 4.0

LLM_METHODS = frozenset(
    {"selenium_nano_llm", "tavily_llm", "agentic_search"}
)
RULE_METHOD = "selenium_rule_based"

# A shared free pool at the upstream provider can throttle everyone at once.
# That is transient and clears on its own, unlike a spent daily allowance, so
# the product is worth retrying instead of ending the run.
TRANSIENT_MARKERS = (
    "upstream_provider_shared_pool",
    "temporarily rate-limited upstream",
)
TRANSIENT_RETRIES = 40
TRANSIENT_WAIT_SECONDS = 300.0


def is_transient(error: Exception) -> bool:
    """Tell an upstream hiccup apart from a spent daily allowance."""

    text = str(error)
    return any(marker in text for marker in TRANSIENT_MARKERS)


def build_evaluator(
    model: str | None = None,
    provider_order: str | None = None,
    max_output_tokens: int | None = None,
):
    """Build the production evaluator, asked the reviewers' question."""

    import sys

    sys.path.insert(0, str(PROJECT_ROOT / "src"))

    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")

    from nano_llm_evaluator import (
        NANO_LLM_PROMPT_VERSION_ALIGNED,
        OpenRouterNanoLLMEvaluator,
        build_relevance_prompt_v2_aligned,
        load_api_keys,
    )

    class AlignedEvaluator(OpenRouterNanoLLMEvaluator):
        prompt_builder = staticmethod(build_relevance_prompt_v2_aligned)
        prompt_version = NANO_LLM_PROMPT_VERSION_ALIGNED

    if max_output_tokens:
        AlignedEvaluator.max_output_tokens = max_output_tokens

    if provider_order:
        # Pin the rerun to the provider that served the results it will be
        # compared against, so routing is not a second changed variable.
        AlignedEvaluator.provider_routing = {
            "order": [provider_order],
            "allow_fallbacks": False,
        }

    return AlignedEvaluator(
        api_keys=load_api_keys(),
        model=model
        or os.environ.get("NANO_LLM_MODEL", "google/gemma-4-26b-a4b-it:free"),
    ), NANO_LLM_PROMPT_VERSION_ALIGNED


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Re-judge stored results with the label-aligned relevance prompt."
        )
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--pacing-seconds",
        type=float,
        default=DEFAULT_PACING_SECONDS,
        help="Pause between calls so the free tier does not throttle bursts.",
    )
    parser.add_argument(
        "--transient-retries",
        type=int,
        default=TRANSIENT_RETRIES,
        help=(
            "How many times to wait out an upstream throttle before giving "
            "up on a product."
        ),
    )
    parser.add_argument(
        "--transient-wait-seconds",
        type=float,
        default=TRANSIENT_WAIT_SECONDS,
        help="How long to wait between those attempts.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Override NANO_LLM_MODEL. Drop the ':free' suffix to leave the "
            "shared free pool and reach the commercial endpoints."
        ),
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=4000,
        help=(
            "Cap the answer length. Without a cap the provider reserves "
            "credit for the whole context window and can refuse the request."
        ),
    )
    parser.add_argument(
        "--provider",
        default=None,
        help=(
            "Pin OpenRouter routing to one provider, e.g. Google, so the "
            "rerun matches the provider behind the existing results."
        ),
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    sources = [PROJECT_ROOT / path for path in manifest["selected_result_files"]]
    evaluator, aligned_version = build_evaluator(
        args.model, args.provider, args.max_output_tokens
    )
    print(f"model: {evaluator.model}  saglayici: {args.provider or 'serbest'}")

    done = copied = skipped = 0
    failure: str | None = None

    for source in sorted(sources):
        payload = json.loads(source.read_text(encoding="utf-8"))
        method = payload["method"]
        target = args.output / method / source.name
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            skipped += 1
            continue

        if method == RULE_METHOD:
            shutil.copyfile(source, target)
            copied += 1
            continue

        if method not in LLM_METHODS:
            continue

        print(
            f"  {time.strftime('%H:%M:%S')} basliyor "
            f"{payload['product_id']:8} {method}",
            flush=True,
        )
        started = time.time()

        rejudged = None

        for attempt in range(1, args.transient_retries + 1):
            try:
                rejudged = evaluator.evaluate_results(
                    payload["keyword"], payload["results"]
                )
                break
            except Exception as error:  # noqa: BLE001 - reason must be visible
                if not is_transient(error) or attempt == args.transient_retries:
                    failure = f"{payload['product_id']}/{method}: {error}"
                    print(f"  DURDU {failure}", flush=True)
                    break

                print(
                    f"  {time.strftime('%H:%M:%S')} saglayici gecici olarak "
                    f"tikali, {args.transient_wait_seconds:.0f}s sonra tekrar "
                    f"({attempt}/{args.transient_retries})",
                    flush=True,
                )
                time.sleep(args.transient_wait_seconds)

        if rejudged is None:
            break

        payload["results"] = rejudged
        payload["prompt_version"] = aligned_version
        # Record what actually produced these judgements. Carrying the
        # original model id forward would make the file claim an endpoint it
        # never used, which is exactly the confusion this rerun exists to
        # avoid.
        payload["model"] = evaluator.model
        payload["rejudged_provider"] = args.provider or "openrouter-auto"
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        done += 1
        said_yes = sum(1 for item in rejudged if item["predicted_relevant"])
        print(
            f"  {time.strftime('%H:%M:%S')} bitti    "
            f"{payload['product_id']:8} {method:20} "
            f"uygun={said_yes}/{len(rejudged)} ({time.time() - started:.0f}s)",
            flush=True,
        )
        time.sleep(args.pacing_seconds)

    written = sum(1 for _ in args.output.rglob("*.json"))

    print()
    print(f"yeniden degerlendirilen : {done}")
    print(f"degismeden kopyalanan   : {copied}")
    print(f"zaten mevcut (atlanan)  : {skipped}")
    print(f"toplam dosya            : {written}/{len(sources)}")

    if failure:
        print()
        print("Kalan dosyalar icin ayni komutu tekrar calistirin;")
        print("tamamlananlar atlanir. Gunluk kota 00:00 UTC'de sifirlanir.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
