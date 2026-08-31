# Workflow Contracts

Use structured intermediate artifacts so analysis, decisions, planning, execution, and validation remain separable. The fields below are the single active contract; never ask the user to choose another prompt, policy, storage, or layout version.

## Fixed configuration

```json
{
  "topic_representation": "plain-text-labels",
  "layout_mode": "shallow-materialized"
}
```

These values are constants. `schema_version` identifies a JSON shape for validation and is not a user-selectable workflow version.

## Common envelope

```json
{
  "schema_version": "kb-workflow/1.0",
  "run_id": "string",
  "stage": "L0|L1|L2|L3|L4|L5|L6",
  "input_fingerprint": "string|null",
  "status": "ok|needs_review|blocked|invalid_input",
  "result": {},
  "issues": [],
  "next_stage": {
    "allowed": true,
    "stage": "L1|L2|L3|L4|L5|L6|null",
    "reason": "string"
  }
}
```

Missing strings are `null`; missing collections are empty arrays. Do not hide uncertainty in prose. Validate an artifact with `python3 scripts/validate_artifact.py artifact.json`.

## Evidence reference

```json
{
  "location": "heading, Frontmatter key, or line reference",
  "excerpt": "short supporting excerpt",
  "support": "direct|indirect|insufficient"
}
```

Every semantic or classification decision includes evidence references.

## L4 operation

```json
{
  "operation_id": "string",
  "transaction_id": "string",
  "type": "append_frontmatter|update_frontmatter|update_inbound_link|update_relation_registry|update_state_registry|create_directory|move_bundle",
  "target_path": "run-root-relative path",
  "target_selector": "field, link, relation id, or null",
  "payload": {},
  "preconditions": ["exact, testable conditions"],
  "expected_sha256": "string|null",
  "expected_effect": ["string"],
  "risk": "low|medium|high",
  "reversible": true,
  "rollback": "string",
  "approval_required": true
}
```

An operation cannot be approved by description alone. Approval names exact operation IDs and paths.

An `update_frontmatter` payload contains one top-level property update:

```json
{
  "property": "topics",
  "expected_old_value": [],
  "new_value": ["approved topic label"]
}
```

Bind the exact property selector, current file SHA-256, expected old value, approved new value, rollback value, and operation ID. Do not update nested objects or several properties in one operation.

A `move_bundle` payload preserves the existing bundle name and uses exactly one topic level:

```json
{
  "source_path": "Article Bundle",
  "destination_path": "Approved Topic/Article Bundle",
  "expected_manifest_sha256": "hex digest",
  "primary_topic": "Approved Topic"
}
```

Require `destination_path` to equal `<primary_topic>/<source folder name>` relative to the run root. A separate `create_directory` operation may create only the exact first-level topic directory. Bind source existence, destination absence, complete bundle manifest, recoverable snapshot, affected inbound path-qualified links, relation-path updates, rollback, and operation dependencies.

## Approval record

```json
{
  "plan_id": "string",
  "approved_operation_ids": ["string"],
  "approved_paths": ["string"],
  "approved_at": "ISO-8601 timestamp",
  "high_risk_authorized": false
}
```

## Relation registry

`<run-root>/.knowledge-curator/relations.json` is the only machine-managed cross-file relation artifact. All paths are relative to the selected run root:

```json
{
  "schema_version": "knowledge-relations/1.0",
  "managed_by": "obsidian-knowledge-curator",
  "relations": [
    {
      "id": "rel-example-prerequisite-target",
      "source_path": "Foundations/Example/Example.md",
      "predicate": "prerequisite_for",
      "target_path": "Systems/Target/Target.md",
      "evidence": "approved classification decision"
    }
  ]
}
```

An `update_relation_registry` operation binds the exact registry SHA-256 when it exists, or explicit absence on first creation, plus the expected old relation or absence, approved replacement, stable relation ID, and rollback. Serialize UTF-8 JSON with two-space indentation, a trailing newline, and relations sorted by `id`. Do not create relation or topic-specification Markdown files.

## Incremental state

`<run-root>/.knowledge-curator/state.json` records validated managed state but does not define a second topic authority:

```json
{
  "schema_version": "knowledge-state/1.0",
  "managed_by": "obsidian-knowledge-curator",
  "layout_mode": "shallow-materialized",
  "last_successful_run_id": "string",
  "documents": [
    {
      "note_path": "Approved Topic/Article/Article.md",
      "bundle_path": "Approved Topic/Article",
      "note_sha256": "hex digest",
      "bundle_manifest_sha256": "hex digest",
      "primary_topic": "Approved Topic",
      "topics": ["Additional Topic"]
    }
  ]
}
```

Sort `documents` by `note_path`; require unique note and bundle paths. `update_state_registry` binds the previous state SHA-256 or explicit absence, exact validated records for changed bundles, untouched prior records, run ID, and rollback. Serialize with two-space indentation and a trailing newline. Do not change `last_successful_run_id` or rewrite the file when no managed state changed.

## Temporary artifacts

For a small request, keep workflow artifacts in context. For a batch, use a temporary run directory outside the selected root unless the user explicitly asks to archive them. The only persistent workflow files inside the root are `.knowledge-curator/state.json` and `.knowledge-curator/relations.json`.
