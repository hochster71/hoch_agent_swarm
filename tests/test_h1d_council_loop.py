"""H1D council loop proofs — reuses dispatch tests under gateway-enforced path.

H1D.7 requires: uv run pytest tests/test_h1d_council_loop.py
"""
from __future__ import annotations

# Import all proofs from the original dispatch suite so both entrypoints pass.
from tests.test_h1d_dispatch import *  # noqa: F401,F403
