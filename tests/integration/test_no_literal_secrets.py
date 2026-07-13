"""Recurrence guard (installed by self_heal) — HOCH source must contain NO literal secrets.
This immunizes against the fixture-secret failure: seeded-fault patterns must be assembled at
runtime, never committed as literals. If this fails, a literal secret pattern is in the source."""
from pathlib import Path
from backend.swarm.cyber_swarm import scan_secrets

ROOT = Path(__file__).resolve().parent.parent.parent
SCAN_DIRS = ['backend', 'scripts', 'config', 'tests', 'frontend', 'deploy']


def test_no_literal_secrets_in_hoch_source():
    hits = []
    for d in SCAN_DIRS:
        root = ROOT / d
        if root.exists():
            for f in scan_secrets(root):
                if f['file'] == 'gitleaks.toml':
                    continue
                hits.append(d + '/' + f['file'] + ' :: ' + f['category'])
    assert not hits, 'literal secret(s) in HOCH source: ' + '; '.join(hits)
