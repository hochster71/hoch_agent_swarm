# Feature Boundary — RMF Evidence Review Companion

To satisfy private-first doctrine and ensure zero exposure of internal swarm architectures, the following features are strictly **out of scope**:

## Excluded Features
* **No remote API dependencies**: The app must not communicate with external APIs or remote relays.
* **No autonomous agent execution**: Swarm pipelines, critique loops, and local LLMs must not run inside the client.
* **No prompt registries**: Prompts used to evaluate or score compliance must not be packaged inside the binary.
