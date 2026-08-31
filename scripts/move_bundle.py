#!/usr/bin/env python3
"""Dry-run or atomically move one article bundle into one topic directory."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path


class MoveError(RuntimeError):
    pass


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bundle_manifest(bundle: Path) -> tuple[str, int]:
    records: list[str] = []
    for path in sorted(bundle.rglob("*"), key=lambda item: item.relative_to(bundle).as_posix()):
        relative = path.relative_to(bundle).as_posix()
        if path.is_symlink():
            raise MoveError(f"bundle contains unsupported symlink: {relative}")
        if path.is_dir():
            records.append(f"D\t{relative}\n")
        elif path.is_file():
            records.append(
                f"F\t{relative}\t{path.stat().st_size}\t{file_sha256(path)}\n"
            )
        else:
            raise MoveError(f"bundle contains unsupported filesystem entry: {relative}")
    encoded = "".join(records).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), len(records)


def safe_relative(value: str, field: str) -> Path:
    path = Path(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise MoveError(f"{field} must be a safe run-root-relative path")
    return path


def inside_root(path: Path, root: Path, field: str) -> None:
    if path == root or root not in path.parents:
        raise MoveError(f"{field} must resolve inside the run root")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", "--vault-root", dest="root", required=True, type=Path)
    parser.add_argument("--source", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--approved-operation-id")
    args = parser.parse_args()

    try:
        root = args.root.resolve(strict=True)
        source_relative = safe_relative(args.source, "source")
        destination_relative = safe_relative(args.destination, "destination")

        if len(destination_relative.parts) != 2:
            raise MoveError("destination must be <primary_topic>/<bundle name>")
        if source_relative.name != destination_relative.name:
            raise MoveError("destination must preserve the source bundle name")

        destination_parent = (root / destination_relative.parent).resolve(strict=True)
        inside_root(destination_parent, root, "destination parent")
        if destination_parent.parent != root or not destination_parent.is_dir():
            raise MoveError("destination topic must be an existing first-level directory")
        destination = destination_parent / destination_relative.name

        source_unresolved = root / source_relative
        source_exists = source_unresolved.exists()
        destination_exists = destination.exists()

        if source_exists and destination_exists:
            raise MoveError("both source and destination exist")

        if not source_exists:
            if not destination_exists or not destination.is_dir():
                raise MoveError("source is missing and destination is not satisfied")
            digest, entries = bundle_manifest(destination)
            print(f"source={source_relative.as_posix()}")
            print(f"destination={destination_relative.as_posix()}")
            print(f"manifest_sha256={digest}")
            print(f"entries={entries}")
            if args.apply:
                if args.expected_manifest_sha256 != digest:
                    raise MoveError("destination manifest does not match approved manifest")
                if not args.approved_operation_id:
                    raise MoveError("apply requires an approved operation ID")
            print(
                "ALREADY_SATISFIED"
                + (
                    f" operation={args.approved_operation_id}"
                    if args.approved_operation_id
                    else ""
                )
            )
            return 0

        source = source_unresolved.resolve(strict=True)
        inside_root(source, root, "source")
        if source.is_symlink() or not source.is_dir():
            raise MoveError("source must be a real directory")
        if source.parent != root and source.parent.parent != root:
            raise MoveError("source bundle must be at the run root or under one topic")

        digest, entries = bundle_manifest(source)
        print(f"source={source_relative.as_posix()}")
        print(f"destination={destination_relative.as_posix()}")
        print(f"manifest_sha256={digest}")
        print(f"entries={entries}")

        if not args.apply:
            print("DRY_RUN")
            return 0
        if args.expected_manifest_sha256 != digest:
            raise MoveError("source manifest does not match approved manifest")
        if not args.approved_operation_id:
            raise MoveError("apply requires an approved operation ID")

        os.replace(source, destination)
        try:
            revised_digest, _ = bundle_manifest(destination)
            if revised_digest != digest:
                raise MoveError("post-move manifest mismatch")
        except Exception:
            if not source.exists() and destination.exists():
                os.replace(destination, source)
            raise

        print(f"APPLIED operation={args.approved_operation_id}")
        return 0
    except (MoveError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
