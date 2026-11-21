# Generation Architecture

Phase 4 follows the Phase 3 evidence package as its factual source of truth.

Flow:

1. User generation configuration.
2. Content strategy plan.
3. Provider-independent text generation.
4. Claim grounding validation.
5. Controlled correction and revalidation.
6. Explainable quality assessment.
7. Durable generation history.

The implementation is provider-independent through `TextGenerationProvider`. Gemini is registered as the built-in text adapter. No provider response is persisted as verified without grounding validation.
