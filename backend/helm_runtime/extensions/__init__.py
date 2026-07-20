"""HELM constitutional-runtime EXTENSIONS (A7 remediation, 2026-07-19).

Composed, separately governed modules that extend the FROZEN constitutional core
(verification target d8d5139a) without modifying its bytes. Doctrine: new capability
= new files + composition, never in-place edits of frozen targets.

Extensions must: fail closed if unavailable; carry a version identifier; expose
deterministic inputs/outputs; generate evidence; be independently testable; and are
prohibited from changing their own authorization status.
"""
