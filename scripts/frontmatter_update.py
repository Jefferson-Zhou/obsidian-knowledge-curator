#!/usr/bin/env python3
"""Safely update one existing top-level Obsidian Frontmatter property."""

from __future__ import annotations

import argparse
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


KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?$")


class UpdateError(RuntimeError):
    pass


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_frontmatter(text: str) -> tuple[str, list[str], list[str], str]:
    bom = "\ufeff" if text.startswith("\ufeff") else ""
    content = text[len(bom) :]
    newline = "\r\n" if "\r\n" in content else "\n"
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise UpdateError("target has no opening Frontmatter delimiter")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return bom, lines[1:index], lines[index + 1 :], newline
    raise UpdateError("opening Frontmatter delimiter has no closing delimiter")


def field_ranges(frontmatter: list[str]) -> dict[str, tuple[int, int]]:
    starts: list[tuple[str, int]] = []
    for index, line in enumerate(frontmatter):
        if line[:1].isspace():
            continue
        match = KEY_RE.match(line.rstrip("\r\n"))
        if match:
            starts.append((match.group(1), index))
    keys = [key for key, _ in starts]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise UpdateError(f"duplicate top-level keys: {', '.join(duplicates)}")
    ranges: dict[str, tuple[int, int]] = {}
    for position, (key, start) in enumerate(starts):
        end = starts[position + 1][1] if position + 1 < len(starts) else len(frontmatter)
        ranges[key] = (start, end)
    return ranges


def parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value == "":
        return None
    if value == "[]":
        return []
    if value in {"null", "~"}:
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def parse_value(key: str, lines: list[str]) -> Any:
    first = lines[0].rstrip("\r\n")
    match = KEY_RE.match(first)
    if not match or match.group(1) != key:
        raise UpdateError(f"cannot parse property: {key}")
    inline = match.group(2) or ""
    if inline.strip():
        if len(lines) != 1:
            raise UpdateError(f"unsupported mixed scalar/block property: {key}")
        return parse_scalar(inline)
    if len(lines) == 1:
        return None
    values: list[Any] = []
    for line in lines[1:]:
        item = line.rstrip("\r\n")
        item_match = re.match(r"^\s+-\s+(.*)$", item)
        if not item_match:
            raise UpdateError(f"unsupported nested or multiline property: {key}")
        parsed = parse_scalar(item_match.group(1))
        if isinstance(parsed, (list, dict)):
            raise UpdateError(f"nested list/object item is unsupported: {key}")
        values.append(parsed)
    return values


def scalar(value: Any, key: str) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if not isinstance(value, str):
        raise UpdateError(f"unsupported scalar for {key}: {type(value).__name__}")
    return json.dumps(value, ensure_ascii=False)


def yaml_lines(key: str, value: Any, newline: str) -> list[str]:
    if isinstance(value, list):
        if not value:
            return [f"{key}: []{newline}"]
        result = [f"{key}:{newline}"]
        for item in value:
            if isinstance(item, (list, dict)):
                raise UpdateError(f"nested list/object item is unsupported: {key}")
            result.append(f"  - {scalar(item, key)}{newline}")
        return result
    if isinstance(value, dict):
        raise UpdateError(f"nested objects are unsupported: {key}")
    rendered = scalar(value, key)
    return [f"{key}:{' ' + rendered if rendered else ''}{newline}"]


def one_property(path: Path, label: str) -> tuple[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or len(value) != 1:
        raise UpdateError(f"{label} JSON must contain exactly one property")
    return next(iter(value.items()))


def update(text: str, expected: tuple[str, Any], proposed: tuple[str, Any]) -> tuple[str, Any, Any]:
    expected_key, expected_value = expected
    proposed_key, proposed_value = proposed
    if expected_key != proposed_key:
        raise UpdateError("expected-old and new-value properties must match")
    bom, frontmatter, body, newline = split_frontmatter(text)
    ranges = field_ranges(frontmatter)
    if proposed_key not in ranges:
        raise UpdateError(f"property does not exist: {proposed_key}")
    start, end = ranges[proposed_key]
    current_value = parse_value(proposed_key, frontmatter[start:end])
    if current_value == proposed_value:
        return text, current_value, proposed_value
    if current_value != expected_value:
        raise UpdateError(
            f"old-value mismatch for {proposed_key}: expected {expected_value!r}, found {current_value!r}"
        )
    replacement = yaml_lines(proposed_key, proposed_value, newline)
    revised_frontmatter = frontmatter[:start] + replacement + frontmatter[end:]
    revised = bom + f"---{newline}" + "".join(revised_frontmatter) + f"---{newline}" + "".join(body)
    return revised, current_value, proposed_value


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
    parser.add_argument("--expected-old-json", required=True, type=Path)
    parser.add_argument("--new-value-json", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--approved-operation-id")
    args = parser.parse_args()

    try:
        root = args.root.resolve(strict=True)
        relative = Path(args.target)
        if relative.is_absolute():
            raise UpdateError("target must be run-root-relative")
        target = (root / relative).resolve(strict=True)
        if target != root and root not in target.parents:
            raise UpdateError("target resolves outside run root")
        if target.suffix.lower() != ".md" or not target.is_file():
            raise UpdateError("target must be an existing Markdown file")

        original = target.read_text(encoding="utf-8")
        current_hash = sha256(original)
        expected = one_property(args.expected_old_json, "expected-old")
        proposed = one_property(args.new_value_json, "new-value")
        revised, current_value, new_value = update(original, expected, proposed)

        print(f"sha256={current_hash}")
        print(f"property={proposed[0]}")
        print(f"current_value={json.dumps(current_value, ensure_ascii=False)}")
        print(f"new_value={json.dumps(new_value, ensure_ascii=False)}")
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
            if not args.approved_operation_id:
                raise UpdateError("apply requires an approved operation ID")
            if revised == original:
                print(f"ALREADY_SATISFIED operation={args.approved_operation_id}")
                return 0
            if not args.expected_sha256 or args.expected_sha256 != current_hash:
                raise UpdateError("apply requires the matching expected SHA-256")
            atomic_write(target, revised)
            print(f"APPLIED operation={args.approved_operation_id}")
        return 0
    except (UpdateError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
