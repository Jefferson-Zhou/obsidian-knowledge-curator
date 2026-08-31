#!/usr/bin/env python3
"""Validate the machine-managed Obsidian cross-file relation registry."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SCHEMA_VERSION = "knowledge-relations/1.0"
MANAGED_BY = "obsidian-knowledge-curator"
PREDICATES = {
    "prerequisite_for",
    "explains",
    "supports",
    "contradicts",
    "compares_with",
    "applied_in",
    "related_to",
}
SYMMETRIC = {"compares_with", "related_to"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
RELATION_FIELDS = {"id", "source_path", "predicate", "target_path", "evidence"}


def resolve_note(root: Path, value: object, field: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{field} must be a non-empty run-root-relative path")
        return None
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() != ".md":
        errors.append(f"{field} must be a safe run-root-relative Markdown path: {value!r}")
        return None
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        errors.append(f"{field} escapes the selected run root: {value!r}")
        return None
    if not candidate.is_file():
        errors.append(f"{field} does not exist: {value!r}")
        return None
    return candidate


def validate(data: object, root: Path) -> list[str]:
    if not isinstance(data, dict):
        return ["top level must be an object"]

    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if data.get("managed_by") != MANAGED_BY:
        errors.append(f"managed_by must be {MANAGED_BY}")
    relations = data.get("relations")
    if not isinstance(relations, list):
        errors.append("relations must be an array")
        return errors

    ids: set[str] = set()
    edges: set[tuple[str, str, str]] = set()
    ordered_ids: list[str] = []
    for index, relation in enumerate(relations):
        prefix = f"relations[{index}]"
        if not isinstance(relation, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing = sorted(RELATION_FIELDS - relation.keys())
        extra = sorted(relation.keys() - RELATION_FIELDS)
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(missing)}")
        if extra:
            errors.append(f"{prefix} unsupported fields: {', '.join(extra)}")

        relation_id = relation.get("id")
        if not isinstance(relation_id, str) or not ID_RE.fullmatch(relation_id):
            errors.append(f"{prefix}.id has an invalid format")
        else:
            ordered_ids.append(relation_id)
            if relation_id in ids:
                errors.append(f"duplicate relation id: {relation_id}")
            ids.add(relation_id)

        predicate = relation.get("predicate")
        if predicate not in PREDICATES:
            errors.append(f"{prefix}.predicate is invalid: {predicate!r}")

        source = relation.get("source_path")
        target = relation.get("target_path")
        resolve_note(root, source, f"{prefix}.source_path", errors)
        resolve_note(root, target, f"{prefix}.target_path", errors)
        if isinstance(source, str) and isinstance(target, str):
            if source == target:
                errors.append(f"{prefix} cannot relate a note to itself")
            if predicate in SYMMETRIC and source > target:
                errors.append(f"{prefix} symmetric endpoints are not canonically ordered")
            edge = (source, str(predicate), target)
            if predicate in SYMMETRIC:
                edge = (min(source, target), str(predicate), max(source, target))
            if edge in edges:
                errors.append(f"duplicate semantic edge at {prefix}")
            edges.add(edge)

        if not isinstance(relation.get("evidence"), str):
            errors.append(f"{prefix}.evidence must be a string")

    if ordered_ids != sorted(ordered_ids):
        errors.append("relations must be sorted by id")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", "--vault-root", dest="root", required=True, type=Path)
    parser.add_argument(
        "--registry", default=".knowledge-curator/relations.json", type=Path
    )
    args = parser.parse_args()

    try:
        root = args.root.resolve(strict=True)
        if args.registry.is_absolute() or ".." in args.registry.parts:
            raise ValueError("registry must be a safe run-root-relative path")
        registry = (root / args.registry).resolve(strict=True)
        if registry != root and root not in registry.parents:
            raise ValueError("registry resolves outside run root")
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2

    errors = validate(data, root)
    if errors:
        for error in errors:
            print(f"INVALID: {error}", file=sys.stderr)
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
