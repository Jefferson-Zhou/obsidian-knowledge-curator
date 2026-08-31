#!/usr/bin/env python3
"""Read-only incremental delta scanner for one explicitly selected run root."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from move_bundle import MoveError, bundle_manifest, file_sha256


STATE_SCHEMA = "knowledge-state/1.0"
DELTA_SCHEMA = "knowledge-delta/1.0"
MANAGED_BY = "obsidian-knowledge-curator"
LAYOUT_MODE = "shallow-materialized"
HEX_SHA256 = re.compile(r"[0-9a-f]{64}")


class StateError(RuntimeError):
    pass


def safe_relative(value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise StateError(f"{field} must be a non-empty string")
    path = Path(value)
    if path.is_absolute() or not path.parts or ".." in path.parts or path == Path("."):
        raise StateError(f"{field} must be a safe run-root-relative path")
    return path


def resolve_within(root: Path, relative: Path, field: str) -> Path:
    resolved = (root / relative).resolve(strict=False)
    if resolved == root or root not in resolved.parents:
        raise StateError(f"{field} resolves outside the selected run root")
    return resolved


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StateError(f"{field} must be a non-empty string")
    return value


def validate_document(record: Any, index: int, root: Path) -> dict[str, Any]:
    prefix = f"documents[{index}]"
    if not isinstance(record, dict):
        raise StateError(f"{prefix} must be an object")
    expected_keys = {
        "note_path",
        "bundle_path",
        "note_sha256",
        "bundle_manifest_sha256",
        "primary_topic",
        "topics",
    }
    if set(record) != expected_keys:
        missing = sorted(expected_keys - set(record))
        extra = sorted(set(record) - expected_keys)
        raise StateError(f"{prefix} keys mismatch; missing={missing}, extra={extra}")

    note_relative = safe_relative(record["note_path"], f"{prefix}.note_path")
    bundle_relative = safe_relative(record["bundle_path"], f"{prefix}.bundle_path")
    if len(bundle_relative.parts) != 2:
        raise StateError(f"{prefix}.bundle_path must be <primary_topic>/<bundle name>")
    if note_relative.parent != bundle_relative or note_relative.suffix.lower() != ".md":
        raise StateError(f"{prefix}.note_path must name a Markdown file directly inside its bundle")

    primary_topic = require_string(record["primary_topic"], f"{prefix}.primary_topic")
    if bundle_relative.parts[0] != primary_topic:
        raise StateError(f"{prefix}.primary_topic must equal the first bundle path component")
    topics = record["topics"]
    if not isinstance(topics, list) or any(not isinstance(item, str) or not item for item in topics):
        raise StateError(f"{prefix}.topics must be a list of non-empty strings")
    if len(topics) > 5:
        raise StateError(f"{prefix}.topics must contain at most five labels")
    if len(topics) != len(set(topics)) or primary_topic in topics:
        raise StateError(f"{prefix}.topics must be unique and exclude primary_topic")

    for key in ("note_sha256", "bundle_manifest_sha256"):
        value = record[key]
        if not isinstance(value, str) or HEX_SHA256.fullmatch(value) is None:
            raise StateError(f"{prefix}.{key} must be a lowercase SHA-256 digest")

    resolve_within(root, note_relative, f"{prefix}.note_path")
    resolve_within(root, bundle_relative, f"{prefix}.bundle_path")
    return record


def load_state(state_path: Path, root: Path) -> dict[str, Any]:
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StateError("BOOTSTRAP_REQUIRED: state file does not exist") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise StateError(f"state file cannot be read: {exc}") from exc

    if not isinstance(data, dict):
        raise StateError("state must be an object")
    expected_keys = {
        "schema_version",
        "managed_by",
        "layout_mode",
        "last_successful_run_id",
        "documents",
    }
    if set(data) != expected_keys:
        missing = sorted(expected_keys - set(data))
        extra = sorted(set(data) - expected_keys)
        raise StateError(f"state keys mismatch; missing={missing}, extra={extra}")
    if data["schema_version"] != STATE_SCHEMA:
        raise StateError(f"schema_version must be {STATE_SCHEMA}")
    if data["managed_by"] != MANAGED_BY:
        raise StateError(f"managed_by must be {MANAGED_BY}")
    if data["layout_mode"] != LAYOUT_MODE:
        raise StateError(f"layout_mode must be {LAYOUT_MODE}")
    require_string(data["last_successful_run_id"], "last_successful_run_id")
    documents = data["documents"]
    if not isinstance(documents, list):
        raise StateError("documents must be a list")

    validated = [validate_document(record, index, root) for index, record in enumerate(documents)]
    note_paths = [record["note_path"] for record in validated]
    bundle_paths = [record["bundle_path"] for record in validated]
    if note_paths != sorted(note_paths):
        raise StateError("documents must be sorted by note_path")
    if len(note_paths) != len(set(note_paths)):
        raise StateError("note_path values must be unique")
    if len(bundle_paths) != len(set(bundle_paths)):
        raise StateError("bundle_path values must be unique")
    return data


def find_new_candidates(root: Path, managed_topics: set[str]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for bundle in sorted(root.iterdir(), key=lambda item: item.name):
        if bundle.name.startswith(".") or bundle.name in managed_topics:
            continue
        if bundle.is_symlink() or not bundle.is_dir():
            continue
        note = bundle / f"{bundle.name}.md"
        if note.is_symlink() or not note.is_file():
            continue
        candidates.append(
            {
                "bundle_path": bundle.name,
                "note_path": note.relative_to(root).as_posix(),
            }
        )
    return candidates


def scan(root: Path, state_relative: Path) -> dict[str, Any]:
    state_path = resolve_within(root, state_relative, "state")
    state = load_state(state_path, root)
    unchanged: list[str] = []
    modified: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []

    for record in state["documents"]:
        note_relative = Path(record["note_path"])
        bundle_relative = Path(record["bundle_path"])
        note = resolve_within(root, note_relative, "note_path")
        bundle = resolve_within(root, bundle_relative, "bundle_path")
        if not bundle.is_dir() or not note.is_file():
            missing.append(
                {
                    "note_path": note_relative.as_posix(),
                    "bundle_path": bundle_relative.as_posix(),
                }
            )
            continue
        reasons: list[str] = []
        if file_sha256(note) != record["note_sha256"]:
            reasons.append("note_sha256_changed")
        manifest_sha256, _ = bundle_manifest(bundle)
        if manifest_sha256 != record["bundle_manifest_sha256"]:
            reasons.append("bundle_manifest_sha256_changed")
        if reasons:
            modified.append({"note_path": note_relative.as_posix(), "reasons": reasons})
        else:
            unchanged.append(note_relative.as_posix())

    managed_topics = {record["primary_topic"] for record in state["documents"]}
    new_candidates = find_new_candidates(root, managed_topics)
    if missing:
        status = "DRIFT_DETECTED"
    elif modified or new_candidates:
        status = "CHANGES_DETECTED"
    else:
        status = "NO_CHANGES"
    return {
        "schema_version": DELTA_SCHEMA,
        "run_root": str(root),
        "state_path": state_relative.as_posix(),
        "status": status,
        "summary": {
            "unchanged": len(unchanged),
            "modified": len(modified),
            "missing": len(missing),
            "new_candidates": len(new_candidates),
        },
        "unchanged": unchanged,
        "modified": modified,
        "missing": missing,
        "new_candidates": new_candidates,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        "--vault-root",
        dest="root",
        required=True,
        type=Path,
        help="exact user-selected highest managed folder; its name is arbitrary",
    )
    parser.add_argument("--state", default=".knowledge-curator/state.json", type=Path)
    args = parser.parse_args()

    try:
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise StateError("root must be a directory")
        state_relative = safe_relative(args.state.as_posix(), "state")
        report = scan(root, state_relative)
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False))
        return 0
    except StateError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 3 if str(exc).startswith("BOOTSTRAP_REQUIRED:") else 2
    except (OSError, MoveError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
