#!/usr/bin/env python3
"""Validate the shared Obsidian knowledge-curator workflow envelope."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


STAGES = {f"L{i}" for i in range(7)}
STATUSES = {"ok", "needs_review", "blocked", "invalid_input"}
REQUIRED = {
    "schema_version",
    "run_id",
    "stage",
    "input_fingerprint",
    "status",
    "result",
    "issues",
    "next_stage",
}


def validate(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["top level must be an object"]

    errors: list[str] = []
    missing = sorted(REQUIRED - data.keys())
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
    if data.get("schema_version") != "kb-workflow/1.0":
        errors.append("schema_version must be kb-workflow/1.0")
    if data.get("stage") not in STAGES:
        errors.append("stage must be one of L0-L6")
    if data.get("status") not in STATUSES:
        errors.append("status has an invalid value")
    if not isinstance(data.get("result"), dict):
        errors.append("result must be an object")
    if not isinstance(data.get("issues"), list):
        errors.append("issues must be an array")

    next_stage = data.get("next_stage")
    if not isinstance(next_stage, dict):
        errors.append("next_stage must be an object")
    else:
        if not isinstance(next_stage.get("allowed"), bool):
            errors.append("next_stage.allowed must be boolean")
        value = next_stage.get("stage")
        if value is not None and value not in STAGES - {"L0"}:
            errors.append("next_stage.stage must be null or one of L1-L6")
        if not isinstance(next_stage.get("reason"), str):
            errors.append("next_stage.reason must be a string")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2

    errors = validate(data)
    if errors:
        for error in errors:
            print(f"INVALID: {error}", file=sys.stderr)
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
