# Knowledge Model

Read this reference before classifying or changing notes. It defines the skill's only active topic representation and physical layout.

## Document roles

- `source-note`: one external source is retained, translated, or closely followed.
- `source-summary`: one external source is critically and structurally distilled.
- `concept`: a reusable synthesis that goes beyond one source.
- `map`: an existing user-authored navigation note. The skill never creates one automatically.
- `project`: goal-bounded work with decisions, outputs, or progress.
- `experiment`: hypothesis, design, result, and interpretation.
- `log`: chronological activity or change record.
- `template`: reusable note structure.
- `other`: insufficient evidence or no fitting role.

Choose one primary role. Do not promote a source translation to `concept` merely because it explains a concept well.

## Source-note property profile

When Frontmatter is absent, create base properties in this order:

```yaml
---
title: "Document title"
source:
author: []
published:
created:
description: "Evidence-bounded one- or two-sentence description."
tags: []
type: source-note
primary_topic: "Approved first-level topic"
topics: []
status: collected
---
```

For an existing block, never reorder it to match this example. Append only missing fields named in the approved operation after all existing properties.

### Field meanings

- `title`: note title, not a rewritten marketing headline.
- `source`: exact source URL or identifier; blank when unavailable.
- `author`: list of author names or existing quoted Obsidian links; never invent.
- `published`: source publication date when supported.
- `created`: note creation date when supported by metadata or user context.
- `description`: what the document substantially covers, based on the note.
- `tags`: sparse workflow or provenance labels, not a topic tree.
- `type`: document role.
- `primary_topic`: exactly one approved plain-text label that also names the physical first-level topic directory.
- `topics`: zero to five additional approved plain-text labels.
- `status`: `inbox`, `collected`, `reading`, `distilled`, `active`, or `archived`.

## Topic rules

- The primary topic covers the document's central problem rather than its broadest possible field.
- An additional topic must be substantively developed, not merely mentioned in an appendix, list, example, or related-work sentence.
- Never repeat `primary_topic` in `topics`.
- Prefer a focused, useful topic such as a method family, system area, or theory domain over a generic umbrella.
- Existing first-level directory names and previously approved `primary_topic` values form the current topic vocabulary.
- Match an existing exact label when its meaning fits. Do not silently merge near-synonyms or overloaded terms.
- If two labels compete and neither clearly covers the central problem better, require review.
- An unmatched central concept is a `new_topic_candidate`. Creating its first-level directory and using the new label require explicit approval.
- The skill does not maintain topic-parent relationships. Every first-level topic can stand independently; cross-topic access uses `topics` and typed relations.

## Fixed physical layout

```text
<run-root>/
├── <primary_topic>/
│   └── <existing article folder>/
│       ├── <article>.md
│       └── assets/
└── .knowledge-curator/
    ├── state.json
    └── relations.json
```

- The exact user-selected run root is the highest managed layer regardless of its name.
- Each approved topic is exactly one first-level directory directly beneath the root.
- Do not inspect the parent directory or add an `AI`, `wiki`, `concept`, `知识体系`, or other common wrapper.
- Move an article directory as one complete bundle. Preserve its name and every contained file.
- The immediate first-level directory must exactly equal the note's `primary_topic` string.
- `topics` and relations never create directories.
- Reclassification is one transaction: update `primary_topic`, move the bundle, update affected path-qualified links and relation paths, then validate.
- Do not perform unrelated cleanup such as deleting `.DS_Store`.

## Fixed topic representation

There is no storage-mode choice. Topic values are ordinary YAML strings, and first-level directory names are their physical authority.

- Do not create same-named concept notes.
- Do not create a topic registry, topic-specification Markdown, topic-specification JSON, or generated navigation map.
- Do not require a `wiki` or `concept` directory.
- Do not treat topic strings as broken links.
- Do not merge article bodies into other notes during classification.
- JSON `schema_version` constants belong only to machine state validation and are never presented as alternative workflow versions.

## Relations

Store approved cross-file relations only in `.knowledge-curator/relations.json`; never create a relation Markdown note or inject a managed relation section into article bodies.

Allowed predicates are `prerequisite_for`, `explains`, `supports`, `contradicts`, `compares_with`, `applied_in`, and `related_to`. Interpret `source_path predicate target_path` literally.

Use run-root-relative paths to existing Markdown files. Relation IDs are stable and unique. Sort relations by `id`. `related_to` and `compares_with` are symmetric, so store one canonical edge with the lexicographically smaller path as `source_path`.

## Tags

Use tags for provenance, workflow, or temporary state such as `clippings`, `translation`, or `needs-review`. Do not duplicate topic memberships as a nested tag hierarchy.

## Confidence

- `high`: direct central evidence, a clear approved-label match, and no serious competitor.
- `medium`: direct evidence exists but scopes overlap or a plausible competitor remains.
- `low`: evidence is incomplete, indirect, or insufficient for a stable topic.

Only a high-confidence existing label may proceed without a classification decision pause. A new topic always requires approval, and every write still requires L4-L5 approval.
