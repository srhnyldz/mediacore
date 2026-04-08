#!/usr/bin/env python3
"""Basit API smoke akisi: task olusturur ve sonucu polling ile izler."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit a download task to the API and poll for status.",
    )
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--url", required=True, help="Media URL to submit.")
    parser.add_argument("--platform-hint", default=None)
    parser.add_argument("--output-format", default=None)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--interval", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task_id = create_task(args)
    return poll_task(args.base_url, task_id, args.timeout, args.interval)


def create_task(args: argparse.Namespace) -> str:
    payload = {"url": args.url}

    if args.platform_hint:
        payload["platform_hint"] = args.platform_hint
    if args.output_format:
        payload["output_format"] = args.output_format

    request = urllib.request.Request(
        f"{args.base_url}/api/v1/tasks/downloads",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
            task_id = body["task_id"]
            print(f"Created task: {task_id}")
            return task_id
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"Task creation failed: {exc.code} {error_body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"API is not reachable: {exc}") from exc


def poll_task(base_url: str, task_id: str, timeout: int, interval: int) -> int:
    deadline = time.time() + timeout

    while time.time() < deadline:
        request = urllib.request.Request(
            f"{base_url}/api/v1/tasks/{task_id}",
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise SystemExit(f"Status polling failed: {exc}") from exc

        status = payload.get("status")
        progress = payload.get("progress_percent", 0)
        message = payload.get("message", "")
        print(f"[{status}] {progress}% - {message}")

        if status == "SUCCESS":
            print(json.dumps(payload.get("result", {}), indent=2))
            return 0
        if status == "FAILURE":
            print(json.dumps(payload, indent=2))
            return 1

        time.sleep(interval)

    print("Polling timed out before the task completed.")
    return 2


if __name__ == "__main__":
    sys.exit(main())

