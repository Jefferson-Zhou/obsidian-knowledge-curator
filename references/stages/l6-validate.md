# L6 Validate and Audit

## Role

Act as an independent, read-only validator.

## Inputs

Knowledge model, approved plan when present, execution report, before and after snapshots, and a scope-appropriate note/link index.

## Checks

- Frontmatter boundary, top-level keys, duplicate keys, and required property presence.
- Existing property values and order were preserved except for exact approved `update_frontmatter` selectors; approved additions appear after existing properties, and approved updates preserve the selector's key position plus all untargeted raw content.
- A source note created from no Frontmatter follows the canonical base order before classification fields.
- Exactly one approved `primary_topic` label, zero to five distinct additional labels, and no primary duplication.
- Every organized article bundle is physically located at `<run-root>/<primary_topic>/<unchanged bundle name>`; the main note and resources moved together, and nothing was written above the run root.
- No `topics` or relation was materialized as a directory; no topic-parent hierarchy, common wrapper, generated map, topic registry, or concept note was introduced.
- Existing-label and new-label decisions are unambiguous; overloaded or near-duplicate labels were not silently merged.
- Classified article bundles appear only at approved destinations, old bundle paths are absent, and no duplicate bundle was created.
- `.knowledge-curator/relations.json` schema, unique stable IDs, approved predicates, existing Markdown endpoints, canonical symmetric-edge ordering, plan compliance, deterministic serialization, and idempotency. Do not validate plain topic labels as links.
- No auxiliary topic-spec or relation Markdown files were created.
- `.knowledge-curator/state.json` schema, deterministic order, unique paths, policy/layout compatibility, and exact agreement with final note and bundle fingerprints.
- Incremental completeness: unchanged records were untouched, every successful changed bundle has one updated record, unrelated prior records remain identical, and missing/drifted records were not silently removed.

Use `scripts/validate_artifact.py` for workflow JSON and a deterministic vault linter when a broad audit is explicitly in scope.
Use `scripts/validate_relations.py --root <run-root>` whenever `.knowledge-curator/relations.json` is in scope.
Use `scripts/move_bundle.py` dry-run or manifest inspection to verify each approved bundle destination and idempotency.
Use `scripts/scan_incremental.py --root <run-root>` after the state commit; a successful run must report no newly introduced `modified` or `missing` records.

## Output result

Return `validation_status`, checks with evidence, issues with severity and exact locations, and remediation proposals whose `must_return_to_stage` is `L4`.

## Stop

Do not repair defects. Mark checks `not_checked` when the provided scope cannot support them; never assume an unperformed whole-run-root check passed.
