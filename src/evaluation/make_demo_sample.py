"""Cut a few named products out of the dataset, as input for a live demo.

The keyword generator and the batch runner both select work with ``--limit``,
which takes the first N records. The first three products of the dataset are
three iPhones, so a demo driven by ``--limit 3`` cannot show that the pipeline
handles a book, a cat food and a biscuit as readily as a phone. This writes
two small input files holding named products instead.

It only ever copies records that already exist; nothing is invented, and the
copies carry the same fields as the files they came from. Output goes under
tmp/, which git ignores, so a demo cannot disturb the committed dataset.

    python src/evaluation/make_demo_sample.py --ids ELK001,PET001,SPM001
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRODUCTS = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "processed_products_multicategory.json"
)
DEFAULT_SUBSET = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "evaluation_subset_multicategory.csv"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "tmp" / "demo"


class SampleError(Exception):
    """The requested sample cannot be built."""


def pick(records: list[dict], ids: list[str], source: Path) -> list[dict]:
    by_id = {record["product_id"]: record for record in records}
    missing = [wanted for wanted in ids if wanted not in by_id]

    if missing:
        raise SampleError(
            f"{source.name} icinde bulunamayan kimlik(ler): {', '.join(missing)}"
        )

    return [by_id[wanted] for wanted in ids]


def build_sample(
    ids: list[str],
    products_path: Path,
    subset_path: Path,
    output_directory: Path,
) -> tuple[Path, Path]:
    if not ids:
        raise SampleError("En az bir urun kimligi verilmeli.")

    products = json.loads(products_path.read_text(encoding="utf-8"))

    with subset_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        subset_rows = list(reader)
        subset_fields = list(reader.fieldnames or [])

    picked_products = pick(products, ids, products_path)
    picked_rows = pick(subset_rows, ids, subset_path)

    output_directory.mkdir(parents=True, exist_ok=True)
    products_out = output_directory / "products_small.json"
    subset_out = output_directory / "subset_small.csv"

    products_out.write_text(
        json.dumps(picked_products, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with subset_out.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=subset_fields)
        writer.writeheader()
        writer.writerows(picked_rows)

    return products_out, subset_out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write small demo input files holding the named products."
    )
    parser.add_argument(
        "--ids",
        default="ELK001,PET001,SPM001",
        help="Comma-separated product IDs, in the order they should appear.",
    )
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--subset", type=Path, default=DEFAULT_SUBSET)
    parser.add_argument("--output-directory", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()

    ids = [value.strip() for value in arguments.ids.split(",") if value.strip()]

    try:
        products_out, subset_out = build_sample(
            ids=ids,
            products_path=arguments.products,
            subset_path=arguments.subset,
            output_directory=arguments.output_directory,
        )
    except (SampleError, OSError, json.JSONDecodeError) as error:
        print(f"[HATA] {error}", file=sys.stderr)
        return 1

    print("=== DEMO ORNEKLEMI ===")
    print(f"Urunler:     {len(ids)} ({', '.join(ids)})")
    print(f"Okundu:      {arguments.products.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Okundu:      {arguments.subset.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Yazildi:     {products_out.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Yazildi:     {subset_out.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
