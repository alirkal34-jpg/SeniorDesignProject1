"""Print a slice of any dataset file the pipeline produces.

Every stage of this project writes a file, and the honest way to present a
stage is to open what it just wrote. Most of those files are too large to
read on a projector: 489 products, 399 results, 193 labels. This prints a
few records instead, so a stage can be shown rather than described.

It reads. It never writes, and it never takes a path outside the project.

    python src/evaluation/show.py data/processed/processed_products_multicategory.json --limit 2
    python src/evaluation/show.py data/labels/multicategory_ground_truth.csv --limit 5 --fields url,human_relevant
    python src/evaluation/show.py results_multicategory/tavily_llm --limit 1
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ShowError(Exception):
    """The requested path cannot be displayed."""


def resolve_inside_project(raw_path: str) -> Path:
    """Return the path, refusing anything outside the project directory."""

    candidate = (PROJECT_ROOT / raw_path).resolve()

    try:
        candidate.relative_to(PROJECT_ROOT)
    except ValueError as error:
        raise ShowError(
            f"Path escapes the project directory: {raw_path}"
        ) from error

    if not candidate.exists():
        raise ShowError(f"Not found: {raw_path}")

    return candidate


def newest_file(directory: Path) -> Path:
    """Return the most recently written JSON file in a results directory.

    Result filenames carry a timestamp and a UUID so repeated runs never
    overwrite each other, which means the interesting file after a run is
    simply the newest one.
    """

    candidates = [path for path in directory.rglob("*.json") if path.is_file()]

    if not candidates:
        raise ShowError(f"No JSON file under: {directory}")

    return max(candidates, key=lambda path: path.stat().st_mtime)


def select_fields(record: Any, fields: list[str]) -> Any:
    if not fields or not isinstance(record, dict):
        return record

    return {name: record.get(name) for name in fields}


def keep_ids(records: list[Any], ids: list[str]) -> list[Any]:
    """Return the named records, in the order they were asked for.

    Without this a demo has to build a trimmed copy of a file just to show a
    few interesting rows, and then the audience is looking at the copy rather
    than at what the pipeline actually wrote.
    """

    if not ids:
        return records

    by_id = {
        record["product_id"]: record
        for record in records
        if isinstance(record, dict) and "product_id" in record
    }
    missing = [wanted for wanted in ids if wanted not in by_id]

    if missing:
        raise ShowError(f"Bu kimlikler dosyada yok: {', '.join(missing)}")

    return [by_id[wanted] for wanted in ids]


def take(payload: Any, limit: int, fields: list[str], ids: list[str]) -> Any:
    if isinstance(payload, list):
        selected = keep_ids(payload, ids)
        if not ids:
            selected = selected[:limit]
        return [select_fields(item, fields) for item in selected]

    if ids:
        raise ShowError("--ids yalnizca kayit listesi iceren dosyalarda kullanilir.")

    return select_fields(payload, fields)


def show_json(path: Path, limit: int, fields: list[str], ids: list[str]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    total = len(payload) if isinstance(payload, list) else 1
    print(json.dumps(take(payload, limit, fields, ids), ensure_ascii=False, indent=2))
    print(f"\n{path.relative_to(PROJECT_ROOT).as_posix()}  —  toplam kayit: {total}")


def show_csv(path: Path, limit: int, fields: list[str], ids: list[str]) -> None:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))

    selected = keep_ids(rows, ids) if ids else rows[:limit]

    for index, row in enumerate(selected, start=1):
        print(f"--- satir {index} ---")
        shown = select_fields(row, fields)
        width = max((len(key) for key in shown), default=0)
        for key, value in shown.items():
            print(f"  {key.ljust(width)} : {value}")
        print()

    print(f"{path.relative_to(PROJECT_ROOT).as_posix()}  —  toplam satir: {len(rows)}")


def show_text(path: Path, limit: int) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines[: limit * 10]:
        print(line)
    print(f"\n{path.relative_to(PROJECT_ROOT).as_posix()}  —  toplam satir: {len(lines)}")


def show(path: Path, limit: int, fields: list[str], ids: list[str]) -> None:
    if path.is_dir():
        path = newest_file(path)
        print(f"[en yeni dosya] {path.relative_to(PROJECT_ROOT).as_posix()}\n")

    suffix = path.suffix.lower()

    if suffix == ".json":
        show_json(path, limit, fields, ids)
    elif suffix == ".csv":
        show_csv(path, limit, fields, ids)
    elif suffix in {".md", ".txt", ".log"}:
        show_text(path, limit)
    else:
        raise ShowError(f"Bu dosya turu gosterilemiyor: {suffix or path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print a few records from a pipeline file or results directory."
    )
    parser.add_argument("path", help="Project-relative file or directory.")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument(
        "--fields",
        default="",
        help="Comma-separated field names to keep, in this order.",
    )
    parser.add_argument(
        "--ids",
        default="",
        help=(
            "Comma-separated product IDs to show, in this order, instead of "
            "the first --limit records."
        ),
    )
    arguments = parser.parse_args()

    fields = [name.strip() for name in arguments.fields.split(",") if name.strip()]
    ids = [name.strip() for name in arguments.ids.split(",") if name.strip()]

    try:
        show(resolve_inside_project(arguments.path), arguments.limit, fields, ids)
    except ShowError as error:
        print(f"[HATA] {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
