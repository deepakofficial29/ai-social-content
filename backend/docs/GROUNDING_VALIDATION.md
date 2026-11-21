# Grounding Validation

Grounding is separate from writing quality. Each caption is split into sentences and classified as supported, partially supported, unsupported, contradicted, or non-factual.

Classification uses evidence text overlap and conflict records. Stylistic calls to action and conversational language are not automatically treated as unsupported facts.

For unsupported or contradicted variants, a controlled correction removes the identified sentences and revalidates the result. The original variant and validation remain preserved in the generation record.

Grounding status is heuristic and explainable, not a guarantee of factual correctness.
