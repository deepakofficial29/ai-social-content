# Caption Generation

Generation uses a modular prompt containing the evidence package and structured plan. It requests three approaches by default: direct and concise, storytelling, and engagement-oriented. One to five variants are allowed.

Platform-specific formatting is guided by configuration; exact character limits are not asserted because platform rules change. Official rules and reviewed behavior should be recorded before relying on exact limits.

If a provider fails or returns invalid JSON, the generator creates a conservative evidence-only fallback from direct evidence and records a warning. This fallback is still passed through grounding validation.
