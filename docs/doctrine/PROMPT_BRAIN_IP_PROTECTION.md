# Prompt Brain Intellectual Property Protection Controls

To protect our proprietary IP:

* **Registry Containment**: The central prompt registries (e.g. `hoch_prompt_registry_v3.json`) must remain in git-ignored or private, local storage.
* **Critique & Score Anonymization**: Scoring traces exported for validation must use sanitized, anonymous scenario names without leaking private customer narratives.
* **Internal Audits**: Periodic runs of the verification script enforce these boundaries.
