"""Local presentation dashboard for the Task 1 evaluation pipeline.

The server intentionally exposes only a fixed allowlist of project commands.
It never returns environment variables and it never accepts arbitrary shell
input from the browser.
"""

from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import os
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


PROJECT_ROOT = Path(__file__).resolve().parent
WEB_ROOT = PROJECT_ROOT / "demo_web"
MAX_LOG_CHARACTERS = 300_000
ALLOWED_PREVIEW_SUFFIXES = {".csv", ".json", ".md", ".txt", ".log"}


@dataclass(frozen=True)
class Step:
    id: str
    number: str
    group: str
    title: str
    description: str
    commands: tuple[tuple[str, ...], ...]
    artifacts: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    live: bool = False
    optional: bool = False


TEST_MODULES = (
    "tests.test_dataset_sources",
    "tests.test_demo_dashboard",
    "tests.test_evaluation_subset",
    "tests.test_ground_truth",
    "tests.test_keyword_generator",
    "tests.test_metrics",
    "tests.test_result_validator",
    "tests.test_rule_based_evaluator",
    "tests.test_selenium_collector",
    "tests.test_batch_runners",
)


STEPS: tuple[Step, ...] = (
    Step(
        id="process-data",
        number="01",
        group="Data foundation",
        title="Process the 100-product dataset",
        description=(
            "Loads the raw CSV, validates its schema, cleans values and writes "
            "row-level validation outputs."
        ),
        commands=(("src/data_processor.py",),),
        artifacts=(
            "data/processed/processed_products.csv",
            "data/processed/processed_products.json",
            "data/processed/validation_issues.csv",
        ),
        prerequisites=("data/raw/candidate_smartphone_products_100.csv",),
    ),
    Step(
        id="quality-check",
        number="02",
        group="Data foundation",
        title="Run dataset quality checks",
        description=(
            "Checks 100 unique IDs, duplicate variants and HTTPS source URLs "
            "across the complete dataset."
        ),
        commands=(("src/quality_check.py",),),
        prerequisites=("data/processed/processed_products.csv",),
    ),
    Step(
        id="fixed-keywords",
        number="03",
        group="Keyword layer",
        title="Create the fixed keyword list",
        description=(
            "Builds 100 deterministic keywords so every evaluation method "
            "receives exactly the same experiment input."
        ),
        commands=(("src/keyword_generator.py", "--provider", "fake", "--limit", "100"),),
        artifacts=(
            "data/processed/generated_keywords.json",
            "data/processed/generated_keywords.metadata.json",
        ),
        prerequisites=("data/processed/processed_products.json",),
    ),
    Step(
        id="preview-keywords",
        number="04",
        group="Keyword layer",
        title="Validate and preview keywords",
        description=(
            "Validates product IDs, required fields and duplicates, then "
            "prints three representative keyword records."
        ),
        commands=(("src/keyword_loader.py", "--limit", "3"),),
        artifacts=("data/processed/generated_keywords.json",),
        prerequisites=("data/processed/generated_keywords.json",),
    ),
    Step(
        id="live-keyword-smoke",
        number="05",
        group="Keyword layer",
        title="OpenRouter keyword smoke test",
        description=(
            "Calls the configured live model for three products and saves the "
            "output separately without changing the fixed 100-keyword file."
        ),
        commands=(
            (
                "src/keyword_generator.py",
                "--provider",
                "openrouter",
                "--limit",
                "3",
                "--output",
                "tmp/generated_keywords.live_smoke.json",
            ),
        ),
        artifacts=(
            "tmp/generated_keywords.live_smoke.json",
            "tmp/generated_keywords.live_smoke.metadata.json",
        ),
        prerequisites=("data/processed/processed_products.json",),
        live=True,
        optional=True,
    ),
    Step(
        id="live-four-methods",
        number="06",
        group="Four-method evaluation",
        title="Run the complete Task 1 LangGraph live",
        description=(
            "Loads P001, generates a real OpenRouter keyword, runs all four "
            "live methods, ranks their results and saves the workflow evidence."
        ),
        commands=(
            (
                "src/langgraph_flow.py",
                "--flow",
                "end-to-end",
                "--product-id",
                "P001",
                "--keyword-provider",
                "openrouter",
                "--execution-mode",
                "live",
                "--max-results",
                "5",
                "--save",
            ),
        ),
        artifacts=(
            "reports/langgraph_runs/*.json",
            "reports/langgraph_runs/method_results/selenium_rule_based/*.json",
            "reports/langgraph_runs/method_results/selenium_nano_llm/*.json",
            "reports/langgraph_runs/method_results/tavily_llm/*.json",
            "reports/langgraph_runs/method_results/agentic_search/*.json",
        ),
        prerequisites=(
            "data/evaluation/evaluation_subset.csv",
            "data/processed/generated_keywords.json",
        ),
        live=True,
        optional=True,
    ),
    Step(
        id="validate-results",
        number="07",
        group="Validation & orchestration",
        title="Validate the LangGraph method JSON",
        description=(
            "Checks shared fields, method names, live providers, result limits, "
            "runtime, cost and relevance-score ranges."
        ),
        commands=(
            (
                "src/evaluation/result_validator.py",
                "reports/langgraph_runs/method_results",
            ),
        ),
        artifacts=(
            "reports/langgraph_runs/method_results/selenium_rule_based/*.json",
            "reports/langgraph_runs/method_results/selenium_nano_llm/*.json",
            "reports/langgraph_runs/method_results/tavily_llm/*.json",
            "reports/langgraph_runs/method_results/agentic_search/*.json",
        ),
        prerequisites=("reports/langgraph_runs/method_results",),
    ),
    Step(
        id="langgraph-demo",
        number="08",
        group="Validation & orchestration",
        title="Verify the LangGraph flow offline",
        description=(
            "Repeats the graph structure with deterministic providers for "
            "testing; this is not presented as measured live evidence."
        ),
        commands=(
            (
                "src/langgraph_flow.py",
                "--flow",
                "end-to-end",
                "--product-id",
                "P001",
                "--keyword-provider",
                "fake",
                "--execution-mode",
                "fake",
                "--max-results",
                "5",
            ),
        ),
        prerequisites=("data/processed/processed_products.json",),
    ),
    Step(
        id="tests",
        number="09",
        group="Validation & orchestration",
        title="Run the clean-demo test suite",
        description=(
            "Runs the unit and integration tests that do not depend on the "
            "historical frozen evaluation files."
        ),
        commands=(("-m", "unittest", *TEST_MODULES, "-v"),),
        prerequisites=("tests",),
    ),
    Step(
        id="final-report",
        number="10",
        group="Frozen evaluation",
        title="Recalculate the final comparison",
        description=(
            "Uses the frozen 10-product manifest and human ground truth to "
            "rebuild the 40-run metrics and readable report."
        ),
        commands=(
            ("src/evaluation/final_metrics.py",),
            ("src/evaluation/final_report.py",),
        ),
        artifacts=(
            "reports/final_evaluation_metrics.json",
            "reports/final_evaluation_report.md",
        ),
        prerequisites=(
            "data/evaluation/final_evaluation_manifest.json",
            "data/labels/domain_ground_truth.csv",
        ),
        optional=True,
    ),
)
STEP_BY_ID = {step.id: step for step in STEPS}


def _display_command(arguments: tuple[str, ...]) -> str:
    parts = [Path(sys.executable).name, *arguments]
    return " ".join(f'"{part}"' if " " in part else part for part in parts)


def _safe_project_path(relative_path: str) -> Path:
    if not relative_path or Path(relative_path).is_absolute():
        raise ValueError("Only project-relative artifact paths are allowed.")
    candidate = (PROJECT_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Artifact path escapes the project directory.") from exc
    return candidate


def _artifact_paths(patterns: tuple[str, ...]) -> list[str]:
    found: list[Path] = []
    for pattern in patterns:
        if any(character in pattern for character in "*?["):
            matches = [path for path in PROJECT_ROOT.glob(pattern) if path.is_file()]
            if matches:
                found.append(max(matches, key=lambda path: path.stat().st_mtime))
        else:
            path = PROJECT_ROOT / pattern
            if path.is_file():
                found.append(path)
    return [path.relative_to(PROJECT_ROOT).as_posix() for path in found]


def _count_csv_rows(path: Path) -> int | None:
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _count_json_records(path: Path) -> int | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return len(payload) if isinstance(payload, list) else None


def build_dashboard_snapshot() -> dict[str, Any]:
    metrics_path = PROJECT_ROOT / "reports" / "final_evaluation_metrics.json"
    metrics: dict[str, Any] = {}
    if metrics_path.is_file():
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            metrics = {}

    raw_count = _count_csv_rows(
        PROJECT_ROOT / "data" / "raw" / "candidate_smartphone_products_100.csv"
    )
    keyword_count = _count_json_records(
        PROJECT_ROOT / "data" / "processed" / "generated_keywords.json"
    )
    subset_count = _count_csv_rows(
        PROJECT_ROOT / "data" / "evaluation" / "evaluation_subset.csv"
    )

    steps = []
    for step in STEPS:
        missing = [
            path
            for path in step.prerequisites
            if not (PROJECT_ROOT / path).exists()
        ]
        artifacts = _artifact_paths(step.artifacts)
        steps.append(
            {
                "id": step.id,
                "number": step.number,
                "group": step.group,
                "title": step.title,
                "description": step.description,
                "command": " && ".join(
                    _display_command(command) for command in step.commands
                ),
                "live": step.live,
                "optional": step.optional,
                "runnable": not missing,
                "missing": missing,
                "artifacts": artifacts,
                "has_output": bool(artifacts),
            }
        )

    return {
        "project_root": str(PROJECT_ROOT),
        "stats": {
            "products": raw_count,
            "keywords": keyword_count,
            "evaluation_products": subset_count,
            "methods": metrics.get("method_count", 4),
            "experiments": metrics.get("experiment_count"),
            "labeled_results": metrics.get("labeled_result_count"),
            "accuracy": metrics.get("accuracy"),
        },
        "steps": steps,
    }


class JobManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._active_job_id: str | None = None

    def start(self, step: Step, live_confirmed: bool) -> dict[str, Any]:
        if step.live and not live_confirmed:
            raise PermissionError("Live API/search execution requires confirmation.")

        missing = [
            path
            for path in step.prerequisites
            if not (PROJECT_ROOT / path).exists()
        ]
        if missing:
            raise FileNotFoundError(
                "Required input is missing: " + ", ".join(missing)
            )

        with self._lock:
            if self._active_job_id:
                active = self._jobs.get(self._active_job_id)
                if active and active["status"] == "running":
                    raise RuntimeError(
                        f"Another step is still running: {active['title']}"
                    )
            job_id = uuid.uuid4().hex
            job = {
                "id": job_id,
                "step_id": step.id,
                "title": step.title,
                "status": "running",
                "started_at": time.time(),
                "finished_at": None,
                "duration_seconds": None,
                "exit_code": None,
                "log": "",
                "artifacts": [],
            }
            self._jobs[job_id] = job
            self._active_job_id = job_id

        thread = threading.Thread(
            target=self._run,
            args=(job_id, step),
            daemon=True,
        )
        thread.start()
        return dict(job)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def _append_log(self, job_id: str, text: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["log"] = (job["log"] + text)[-MAX_LOG_CHARACTERS:]

    def _run(self, job_id: str, step: Step) -> None:
        exit_code = 0
        try:
            for arguments in step.commands:
                self._append_log(job_id, f"$ {_display_command(arguments)}\n\n")
                environment = os.environ.copy()
                environment["PYTHONUTF8"] = "1"
                process = subprocess.Popen(
                    [sys.executable, *arguments],
                    cwd=PROJECT_ROOT,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                )
                assert process.stdout is not None
                for line in process.stdout:
                    self._append_log(job_id, line)
                exit_code = process.wait()
                if exit_code:
                    break
        except Exception as exc:  # pragma: no cover - defensive process guard
            exit_code = 1
            self._append_log(job_id, f"\nDashboard error: {exc}\n")
        finally:
            finished_at = time.time()
            with self._lock:
                job = self._jobs[job_id]
                job["status"] = "completed" if exit_code == 0 else "failed"
                job["exit_code"] = exit_code
                job["finished_at"] = finished_at
                job["duration_seconds"] = round(
                    finished_at - job["started_at"], 3
                )
                job["artifacts"] = _artifact_paths(step.artifacts)
                if self._active_job_id == job_id:
                    self._active_job_id = None


JOB_MANAGER = JobManager()


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "Task1Dashboard/1.0"

    def log_message(self, format_string: str, *args: object) -> None:
        return

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "img-src 'self' data:; connect-src 'self'",
        )

    def _send_bytes(
        self,
        payload: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(
        self,
        payload: dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(encoded, "application/json; charset=utf-8", status)

    def _send_error_json(self, message: str, status: HTTPStatus) -> None:
        self._send_json({"error": message}, status)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_static("index.html")
            return
        if parsed.path.startswith("/assets/"):
            self._serve_static(parsed.path.removeprefix("/assets/"))
            return
        if parsed.path == "/api/dashboard":
            self._send_json(build_dashboard_snapshot())
            return
        if parsed.path == "/api/job":
            job_id = parse_qs(parsed.query).get("id", [""])[0]
            job = JOB_MANAGER.get(job_id)
            if not job:
                self._send_error_json("Job not found.", HTTPStatus.NOT_FOUND)
                return
            self._send_json(job)
            return
        if parsed.path == "/api/artifact":
            relative_path = parse_qs(parsed.query).get("path", [""])[0]
            self._serve_artifact(relative_path)
            return
        self._send_error_json("Not found.", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if urlparse(self.path).path != "/api/run":
            self._send_error_json("Not found.", HTTPStatus.NOT_FOUND)
            return
        try:
            content_length = min(int(self.headers.get("Content-Length", "0")), 4096)
            body = json.loads(self.rfile.read(content_length) or b"{}")
            step_id = str(body.get("step_id", ""))
            step = STEP_BY_ID.get(step_id)
            if not step:
                self._send_error_json("Unknown pipeline step.", HTTPStatus.BAD_REQUEST)
                return
            job = JOB_MANAGER.start(
                step=step,
                live_confirmed=body.get("confirm_live") is True,
            )
            self._send_json(job, HTTPStatus.ACCEPTED)
        except PermissionError as exc:
            self._send_error_json(str(exc), HTTPStatus.FORBIDDEN)
        except FileNotFoundError as exc:
            self._send_error_json(str(exc), HTTPStatus.UNPROCESSABLE_ENTITY)
        except RuntimeError as exc:
            self._send_error_json(str(exc), HTTPStatus.CONFLICT)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)

    def _serve_static(self, relative_path: str) -> None:
        requested = (WEB_ROOT / relative_path).resolve()
        try:
            requested.relative_to(WEB_ROOT.resolve())
        except ValueError:
            self._send_error_json("Invalid asset path.", HTTPStatus.BAD_REQUEST)
            return
        if not requested.is_file():
            self._send_error_json("Asset not found.", HTTPStatus.NOT_FOUND)
            return
        mime_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
        if requested.suffix == ".js":
            mime_type = "text/javascript"
        self._send_bytes(requested.read_bytes(), f"{mime_type}; charset=utf-8")

    def _serve_artifact(self, relative_path: str) -> None:
        try:
            requested = _safe_project_path(relative_path)
        except ValueError as exc:
            self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
            return
        if not requested.is_file():
            self._send_error_json("Artifact not found.", HTTPStatus.NOT_FOUND)
            return
        if requested.suffix.lower() not in ALLOWED_PREVIEW_SUFFIXES:
            self._send_error_json(
                "This file type cannot be previewed.",
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            )
            return
        try:
            text = requested.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            self._send_error_json(
                "Artifact is not UTF-8 text.",
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            )
            return
        self._send_json(
            {
                "path": requested.relative_to(PROJECT_ROOT).as_posix(),
                "content": text,
                "size": requested.stat().st_size,
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the local Task 1 presentation dashboard."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if not WEB_ROOT.is_dir():
        raise FileNotFoundError(f"Dashboard assets are missing: {WEB_ROOT}")

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"Task 1 dashboard: {url}")
    print(f"Project root: {PROJECT_ROOT}")
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
