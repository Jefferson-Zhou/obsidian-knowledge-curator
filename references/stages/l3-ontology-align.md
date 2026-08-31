# L3 Ontology Alignment

## Role

Act as a read-only classifier constrained by the approved topic vocabulary.

## Inputs

L1 manifest, L2 semantic profile, knowledge model, existing first-level topic names, prior approved `primary_topic` values, and any exact label decision supplied by the user.

## Task

Confirm the document role. Match candidate topics against exact existing labels and their demonstrated use in prior classified notes. Select one `primary_topic` that best covers the central problem and zero to five additional substantive `topics`.

Put incidental or insufficient candidates in `rejected_topics`. Put unmatched central concepts in `new_topic_candidates`; never use one as a final topic before exact approval. Propose only evidence-backed typed relations.

The fixed representation authorizes plain text labels and one first-level physical topic directory. It never authorizes a concept note, topic registry, generated map, parent hierarchy, body merge, or deeper directory. Model dependencies, prerequisites, comparisons, and applications as typed relations instead of containment.

## Output result

Return `topic_representation: plain-text-labels`, `final_document_type`, `primary_topic`, `topics`, `rejected_topics`, `relations`, `new_topic_candidates`, confidence and evidence for each decision, plus `review.required`, reasons, and competing primary topics.

## Stop

A null, medium-confidence, or low-confidence primary topic, a new-topic candidate, an unresolved label collision, or competing primary topics returns `needs_review` before planning. Never search for a same-named concept file.
