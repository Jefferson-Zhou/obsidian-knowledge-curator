#!/usr/bin/env python3
"""Append missing Obsidian properties while preserving existing Frontmatter."""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any


CORE_ORDER = ["title", "source", "author", "published", "created", "description", "tags"]
KNOWLEDGE_ORDER = ["type", "primary_topic", "topics", "status"]
KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s|$)")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class MergeError(RuntimeError):
    pass


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_frontmatter(text: str) -> tuple[str, list[str] | None, list[str], str]:
    bom = "\ufeff" if text.startswith("\ufeff") else ""
    content = text[len(bom) :]
    newline = "\r\n" if "\r\n" in content else "\n"
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return bom, None, lines, newline
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return bom, lines[1:index], lines[index + 1 :], newline
    raise MergeError("opening Frontmatter delimiter has no closing delimiter")


def existing_keys(frontmatter: list[str]) -> list[str]:
    keys: list[str] = []
    for line in frontmatter:
        match = KEY_RE.match(line)
        if match:
            keys.append(match.group(1))
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise MergeError(f"duplicate top-level keys: {', '.join(duplicates)}")
    return keys


def scalar(value: Any, key: str) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if not isinstance(value, str):
        raise MergeError(f"unsupported scalar for {key}: {type(value).__name__}")
    if key in {"published", "created"} and DATE_RE.fullmatch(value):
        return value
    return json.dumps(value, ensure_ascii=False)


def yaml_lines(key: str, value: Any, newline: str) -> list[str]:
    if isinstance(value, list):
        if not value:
            return [f"{key}: []{newline}"]
        output = [f"{key}:{newline}"]
        for item in value:
            output.append(f"  - {scalar(item, key)}{newline}")
        return output
    if isinstance(value, dict):
        raise MergeError(f"nested objects are not supported for {key}")
    rendered = scalar(value, key)
    suffix = f" {rendered}" if rendered else ""
    return [f"{key}:{suffix}{newline}"]


def ordered_properties(properties: dict[str, Any]) -> list[tuple[str, Any]]:
    order = CORE_ORDER + KNOWLEDGE_ORDER
    result: list[tuple[str, Any]] = []
    for key in order:
        if key in properties:
            result.append((key, properties[key]))
    for key, value in properties.items():
        if key not in order:
            result.append((key, value))
    return result


def defaults(target: Path, profile: str) -> dict[str, Any]:
    role = "source-summary" if profile == "source-summary" else "source-note"
    return {
        "title": target.stem,
        "source": None,
        "author": [],
        "published": None,
        "created": None,
        "description": "",
        "tags": [],
        "type": role,
        "topics": [],
        "status": "collected",
    }


def merge(text: str, target: Path, patch: dict[str, Any], profile: str) -> str:
    bom, frontmatter, body, newline = split_frontmatter(text)
    present = set(existing_keys(frontmatter)) if frontmatter is not None else set()
    proposed_primary = patch.get("primary_topic")
    if "primary_topic" not in present and (
        not isinstance(proposed_primary, str) or not proposed_primary.strip()
    ):
        raise MergeError("an existing or approved non-empty primary_topic label is required")

    if frontmatter is None:
        desired = defaults(target, profile)
        desired.update(patch)
        rendered: list[str] = []
        for key, value in ordered_properties(desired):
            rendered.extend(yaml_lines(key, value, newline))
        return bom + f"---{newline}" + "".join(rendered) + f"---{newline}{newline}" + "".join(body)

    keys = present
    additions: list[str] = []
    for key, value in ordered_properties(patch):
        if key not in keys:
            additions.extend(yaml_lines(key, value, newline))

    preserved = list(frontmatter)
    if preserved and not preserved[-1].endswith(("\n", "\r")):
        preserved[-1] += newline
    return bom + f"---{newline}" + "".join(preserved + additions) + f"---{newline}" + "".join(body)


def atomic_write(path: Path, text: str) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", "--vault-root", dest="root", required=True, type=Path)
    parser.add_argument("--target", required=True)
    parser.add_argument("--properties-json", required=True, type=Path)
    parser.add_argument("--profile", choices=["source-note", "source-summary"], default="source-note")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--approved-operation-id")
    args = parser.parse_args()

    try:
        root = args.root.resolve(strict=True)
        relative = Path(args.target)
        if relative.is_absolute():
            raise MergeError("target must be run-root-relative")
        target = (root / relative).resolve(strict=True)
        if target != root and root not in target.parents:
            raise MergeError("target resolves outside run root")
        if target.suffix.lower() != ".md" or not target.is_file():
            raise MergeError("target must be an existing Markdown file")

        original = target.read_text(encoding="utf-8")
        current_hash = sha256(original)
        patch = json.loads(args.properties_json.read_text(encoding="utf-8"))
        if not isinstance(patch, dict):
            raise MergeError("properties JSON must be an object")
        revised = merge(original, target, patch, args.profile)

        print(f"sha256={current_hash}")
        diff = "".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                revised.splitlines(keepends=True),
                fromfile=str(relative),
                tofile=str(relative),
            )
        )
        if diff:
            print(diff, end="" if diff.endswith("\n") else "\n")
        else:
            print("NO_CHANGES")

        if args.apply:
            if not args.expected_sha256 or args.expected_sha256 != current_hash:
                raise MergeError("apply requires the matching expected SHA-256")
            if not args.approved_operation_id:
                raise MergeError("apply requires an approved operation ID")
            if revised != original:
                atomic_write(target, revised)
                print(f"APPLIED operation={args.approved_operation_id}")
            else:
                print(f"ALREADY_SATISFIED operation={args.approved_operation_id}")
        return 0
    except (MergeError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
