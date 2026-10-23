"""Day 1 発展課題: Gemini モデルと質問の応答時間を比較する。"""

import argparse
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from google import genai
from google.genai import errors, types

from app.config import get_api_key

MODELS = ("gemini-3.5-flash-lite", "gemini-3.8-flash")
QUESTIONS = (
    ("lora", "LoRAとは何ですか？"),
    ("homework_levels", "AIE2026の講座の宿題にある「3レベル」とは何ですか？"),
)
CSV_COLUMNS = (
    "timestamp_utc",
    "model",
    "question_id",
    "repeat",
    "elapsed_seconds",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "status",
)
RESULTS_PATH = (
    Path(__file__).resolve().parent.parent
    / "lectures"
    / "01"
    / "benchmark_results.csv"
)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("1以上を指定してください")
    return parsed


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("0以上を指定してください")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Day 1 のモデル・質問ベンチマーク")
    parser.add_argument("--repeats", type=positive_int, default=3)
    parser.add_argument("--delay-seconds", type=non_negative_float, default=15)
    parser.add_argument("--timeout-seconds", type=positive_int, default=120)
    args = parser.parse_args()

    total_requests = len(MODELS) * len(QUESTIONS) * args.repeats
    existing_keys: set[tuple[str, str, str]] = set()
    if RESULTS_PATH.exists():
        with RESULTS_PATH.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            existing_keys = {
                (row["model"], row["question_id"], row["repeat"])
                for row in reader
            }

    pending_requests = [
        (model, question_id, question, repeat)
        for model in MODELS
        for question_id, question in QUESTIONS
        for repeat in range(1, args.repeats + 1)
        if (model, question_id, str(repeat)) not in existing_keys
    ]
    completed_requests = total_requests - len(pending_requests)
    print(
        f"完了済み件数: {completed_requests}/{total_requests}, "
        f"残り件数: {len(pending_requests)}",
        flush=True,
    )

    client = genai.Client(
        api_key=get_api_key(),
        http_options=types.HttpOptions(
            timeout=args.timeout_seconds * 1000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )

    write_header = (
        not RESULTS_PATH.exists() or RESULTS_PATH.stat().st_size == 0
    )
    with RESULTS_PATH.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=CSV_COLUMNS,
            lineterminator="\n",
        )
        if write_header:
            writer.writeheader()

        for request_index, (model, question_id, question, repeat) in enumerate(
            pending_requests,
            start=1,
        ):
            started_at = time.perf_counter()
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=question,
                )
                elapsed_seconds = time.perf_counter() - started_at
                usage = getattr(response, "usage_metadata", None)
                input_tokens = getattr(usage, "prompt_token_count", None)
                output_tokens = getattr(usage, "candidates_token_count", None)
                total_tokens = getattr(usage, "total_token_count", None)
                status = "ok"
            except httpx.TimeoutException:
                elapsed_seconds = time.perf_counter() - started_at
                input_tokens = None
                output_tokens = None
                total_tokens = None
                status = "timeout"
            except errors.APIError as error:
                elapsed_seconds = time.perf_counter() - started_at
                input_tokens = None
                output_tokens = None
                total_tokens = None
                status = f"error (HTTP {error.code})"

            writer.writerow(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "model": model,
                    "question_id": question_id,
                    "repeat": repeat,
                    "elapsed_seconds": elapsed_seconds,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "status": status,
                }
            )
            csv_file.flush()

            completed_requests += 1
            print(
                f"[{completed_requests}/{total_requests}] model={model} "
                f"question_id={question_id} repeat={repeat}/{args.repeats} "
                f"elapsed_seconds={elapsed_seconds:.3f} status={status}",
                flush=True,
            )

            if request_index < len(pending_requests):
                time.sleep(args.delay_seconds)


if __name__ == "__main__":
    main()