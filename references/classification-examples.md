# Classification Boundary Examples

Use these only when they materially clarify an ambiguous classification. They illustrate the single fixed protocol and do not define a second workflow.

## Central topic with incidental mentions

A systems article centrally explains cache fragmentation, paging, and serving memory management. An appendix briefly lists quantization and speculative decoding.

- Choose the most focused existing systems topic that covers the central explanation.
- Add cache or memory topics only when substantially developed.
- Reject quantization and speculative decoding as incidental mentions.

## Several substantive memberships

A paper centrally studies low-bit cache compression and evaluates memory use and throughput.

- Choose one existing label covering the core compression problem as `primary_topic`.
- Add low-bit quantization and inference-memory labels only when those exact existing labels fit.
- Do not duplicate the note or give it several primary topics.

## Information-insufficient note

A short note says only: “Quantization, distillation, and speculative decoding can optimize inference.”

- Return low confidence and `needs_review`.
- Do not create three topics or classify by title alone.

## Foundation versus application

A document about virtual-memory mechanisms is relevant to an inference system that uses paging.

- Keep the foundation and application as independent first-level topics.
- Express a supported dependency with `prerequisite_for` or `applied_in` in relation JSON.
- Do not place either topic physically beneath the other.

## Overloaded label

Chinese `推理` can mean model reasoning or computational inference.

- Reasoning behavior, reasoning training, and reasoning models require a reasoning-specific label.
- Decoding, serving, scheduling, latency, memory, and throughput require an inference-systems label.
- Do not use an ambiguous bare label until its meaning is approved.
- Do not create a shared parent folder or generated navigation note to combine the senses.
