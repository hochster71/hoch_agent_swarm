#!/usr/bin/env python3
"""node_execution_observer.py — CYB-003. The Node half of the Runtime Evidence Layer.

WHY (founder ruling 2026-07-21). The Python observer was about to be used to "validate" a
vite/esbuild update. The two windows would have been byte-identical — because an npm
package cannot appear in `sys.modules`. That is not a defect in the Python observer; it is
an OBSERVABILITY BOUNDARY, and the discovery of a boundary is more valuable than the patch
that exposed it.

THE RULE THIS ENCODES
    one observer per runtime; one shared evidence schema; scope declared in every artifact.
    The implementation differs. The evidence format does not. Nothing may report on a
    runtime it cannot execute.

WHAT THIS OBSERVES
    Node's actual module resolution, captured by running node with a --require preload
    that hooks Module._load and records every resolved specifier. This is the Node analogue
    of the sys.modules diff: what the runtime ACTUALLY loaded, not what package.json
    declares it might.

WHAT IT DOES NOT OBSERVE — stated for the same reason the Python one now states it:
    python imports, swift/iOS, browser-side execution after bundling, network egress,
    and any package pulled in by a build step that this window does not bracket.

THREAT-MODEL NOTE. vite and esbuild are devDependencies: they run on a developer machine
during `npm run dev` / `npm run build`, not inside any deployed HELM artifact. Evidence
about them belongs to the BUILD assurance lane, not the operational runtime lane. Recording
the distinction is the point — a dev-server CVE and a production RCE are different claims.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]

RUNTIME = "node"
OBSERVES = [
    "node CommonJS resolution (Module._load hook)",
    "node ESM resolution (module.register resolve hook)",
]
DOES_NOT_OBSERVE = [
    "python imports — see backend/helm_runtime/execution_observer.py",
    "modules loaded by child processes the command spawns",
    "swift/iOS runtime",
    "browser-side execution of the built bundle",
    "network egress",
    "packages loaded by build phases outside this window",
]

# npm packages whose LOADING during a build/dev session is security-relevant.
WATCHED: Dict[str, str] = {
    "vite": "dev-server CVEs: server.fs.deny bypass, path traversal in optimized deps",
    "esbuild": "dev server accepts any-origin requests and returns the response",
    "launch-editor": "NTLMv2 hash disclosure via UNC path handling (Windows)",
}

# The preload hook. Kept deliberately tiny and side-effect-free apart from its own log:
# an observer that changes what it observes produces evidence about itself.
_HOOK = r"""
const Module = require('module');
const fs = require('fs');
const out = process.env.HELM_OBS_OUT;
const seen = new Set();
const orig = Module._load;
Module._load = function (request, parent, isMain) {
  try { seen.add(String(request)); } catch (e) {}
  return orig.apply(this, arguments);
};
const flush = () => {
  try { fs.writeFileSync(out, JSON.stringify(Array.from(seen).sort())); } catch (e) {}
};
process.on('exit', flush);
process.on('SIGINT', () => { flush(); process.exit(130); });
process.on('SIGTERM', () => { flush(); process.exit(143); });
"""


# CYB-003 DEFECT-002 (caught by the positive control, 2026-07-21).
# Module._load intercepts require() ONLY. vite 5.4.21 declares "type": "module" and is
# loaded through Node's ESM pipeline, which is a SEPARATE mechanism. The observer therefore
# reported vite NOT LOADED *during a vite build* — structurally unable to see the one
# package the window existed to observe. Both pipelines are now hooked.
_ESM_HOOK = r"""
import { appendFileSync } from 'node:fs';
const out = process.env.HELM_OBS_ESM_OUT;
export async function resolve(specifier, context, next) {
  const r = await next(specifier, context);
  try { appendFileSync(out, r.url + "\n"); } catch (e) {}
  return r;
}
"""

_ESM_BOOT = r"""
import { register } from 'node:module';
import { pathToFileURL } from 'node:url';
register('./helm_esm_hook.mjs', pathToFileURL(process.env.HELM_OBS_HOOK_DIR + '/'));
"""


# CYB-003 INVARIANT (founder, 2026-07-21):
#   An observer shall not emit or support a negative assertion (ABSENT / NOT_LOADED)
#   until it has demonstrated, under substantially equivalent execution conditions,
#   that it can detect the corresponding POSITIVE condition.
#
# Three instrument failures on 2026-07-21 all reported clean while being incapable of
# reporting dirty:  grep ^import mcp  |  split("/")[0] on absolute paths  |  CJS-only
# hooks against an ESM package. The positive control caught all three; self-review caught
# none. So the control is not a test — it is a PRECONDITION, and its result travels with
# the evidence.
POSITIVE_CONTROL = {
    "command": ["npx", "vite", "build", "--logLevel", "error"],
    "must_detect": ["vite", "esbuild"],
    "rationale": "a build that loads vite MUST show vite; if it does not, every "
                 "NOT_LOADED this observer emits is uninterpretable",
}


def run_positive_control(timeout: int = 300) -> Dict[str, Any]:
    """Demonstrate detection of presence. Gates negative reporting."""
    ev = observe_node(POSITIVE_CONTROL["command"],
                      label="_positive_control", timeout=timeout)
    detected = set((ev.get("watched_LOADED") or {}).keys())
    required = set(POSITIVE_CONTROL["must_detect"])
    missing = sorted(required - detected)
    return {
        "positive_controls": {p: ("PASS" if p in detected else "FAIL") for p in required},
        "validated_for_negative_reporting": not missing and ev.get("outcome") == "COMPLETED",
        "missing": missing,
        "control_outcome": ev.get("outcome"),
        "note": ("if validated_for_negative_reporting is false, downstream assurance "
                 "tooling MUST NOT consume any NOT_LOADED assertion from this observer"),
    }


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(o: Any) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


def _node_available() -> Optional[str]:
    exe = shutil.which("node")
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def observe_node(argv: List[str], *, label: str, cwd: Optional[Path] = None,
                 timeout: int = 300) -> Dict[str, Any]:
    """Run a node command with the resolution hook and record what it loaded.

    Fails OPEN for the observation, CLOSED for the claim: if node is missing or the command
    dies, the artifact says UNOBSERVED rather than reporting an empty — i.e. clean — window.
    Absence of evidence must never render as absence of loading.
    """
    started = _now()
    ver = _node_available()
    base: Dict[str, Any] = {
        "schema_version": "HELM_EXECUTION_OBSERVATION_v2",
        "evidence_class": "OBSERVED_EXECUTION",
        "runtime": RUNTIME,
        "observes": OBSERVES,
        "DOES_NOT_OBSERVE": DOES_NOT_OBSERVE,
        "scope_warning": (
            "this artifact covers the node runtime ONLY. Absence of a package here is NOT "
            "evidence about the python runtime, and vice versa."),
        "assurance_lane": "BUILD/DEV — vite and esbuild are devDependencies and do not "
                          "execute inside a deployed HELM artifact",
        "label": label,
        "command": argv,
        "started_at": started,
        "observation_windows": 1,
        "observer_capability": {
            "runtime": RUNTIME,
            "module_systems": ["CommonJS", "ESM"],
            "coverage": ["require()", "import / dynamic import()"],
            "positive_control": POSITIVE_CONTROL["must_detect"],
            "negative_reporting_gated_on": "run_positive_control()",
        },
        "method": "node --require (CJS Module._load) + --import module.register (ESM resolve); "
                  "no package patched",
        "hook_api_note": ("module.register() is used here. Newer Node exposes "
                          "module.registerHooks() as a synchronous alternative; the "
                          "observer should stay abstracted from the hook API so a Node "
                          "upgrade does not silently reduce coverage — the failure mode "
                          "would look exactly like a clean result."),
        "generated_by": "backend.helm_runtime.node_execution_observer.observe_node",
    }

    if not ver:
        base.update({
            "outcome": "UNOBSERVED",
            "reason": "node not available on PATH — the window could not be opened",
            "note": "UNOBSERVED is not OBSERVED_ABSENT. Nothing is claimed about loading.",
            "finished_at": _now(),
        })
        base["content_hash"] = _sha({k: v for k, v in base.items() if k != "content_hash"})
        return base

    with tempfile.TemporaryDirectory() as td:
        cjs_hook = Path(td) / "helm_obs_hook.cjs"
        cjs_hook.write_text(_HOOK)
        (Path(td) / "helm_esm_hook.mjs").write_text(_ESM_HOOK)
        esm_boot = Path(td) / "helm_esm_boot.mjs"
        esm_boot.write_text(_ESM_BOOT)
        outp, esm_out = Path(td) / "loaded.json", Path(td) / "esm.txt"
        esm_out.touch()
        env = dict(os.environ,
                   HELM_OBS_OUT=str(outp), HELM_OBS_ESM_OUT=str(esm_out),
                   HELM_OBS_HOOK_DIR=td,
                   NODE_OPTIONS=f"--require {cjs_hook} --import {esm_boot}")
        try:
            proc = subprocess.run(argv, cwd=str(cwd or ROOT / "frontend"), env=env,
                                  capture_output=True, text=True, timeout=timeout)
            rc, err = proc.returncode, (proc.stderr or "")[-300:]
        except Exception as e:
            rc, err = -1, f"{type(e).__name__}: {e}"[:300]
        cjs = json.loads(outp.read_text()) if outp.exists() else None
        esm = [l for l in esm_out.read_text().splitlines() if l] if esm_out.exists() else []
        loaded = None if (cjs is None and not esm) else (cjs or []) + esm

    if loaded is None:
        base.update({
            "outcome": "UNOBSERVED",
            "reason": "hook produced no output — the command may not have started node",
            "node_version": ver, "exit_code": rc, "stderr_tail": err,
            "note": "UNOBSERVED is not OBSERVED_ABSENT.",
            "finished_at": _now(),
        })
    else:
        # CYB-003 DEFECT-001 (caught by the positive control, 2026-07-21).
        # The first version matched bare specifiers via s.split("/")[0]. Node resolves real
        # packages to ABSOLUTE PATHS (/…/node_modules/vite/dist/node/index.js), so that
        # yielded "" and the observer reported vite NOT LOADED *during a vite build*.
        # Surface-form matching again — the same error as the grep in CYB-001. Match on
        # what the specifier MEANS: a bare name, or a node_modules path segment.
        def _loaded_pkgs(specs: List[str]) -> set:
            found = set()
            for spec in specs:
                for m in re.finditer(r"node_modules/((?:@[^/]+/)?[^/]+)", spec):
                    found.add(m.group(1))
                if not spec.startswith((".", "/")):
                    found.add(spec.split("/")[0] if not spec.startswith("@")
                              else "/".join(spec.split("/")[:2]))
            return found

        tops = _loaded_pkgs(loaded)
        base.update({
            "outcome": "COMPLETED" if rc == 0 else "NONZERO_EXIT",
            "node_version": ver, "exit_code": rc, "stderr_tail": err if rc else "",
            "modules_resolved_during_window": len(loaded),
            "resolved_via_commonjs": len(cjs or []),
            "resolved_via_esm": len(esm),
            "distinct_packages_resolved": len(tops),
            "watched_LOADED": {w: {"why_watched": why} for w, why in WATCHED.items()
                               if w in tops},
            "watched_NOT_LOADED_in_this_run": [w for w in WATCHED if w not in tops],
            "claim_this_supports": (
                "OBSERVED_ABSENT_IN_THIS_RUN for the not-loaded set — NOT 'unreachable'. "
                "One window is one observation, in one runtime."),
            "finished_at": _now(),
        })
    base["content_hash"] = _sha({k: v for k, v in base.items() if k != "content_hash"})
    return base


def write_evidence(ev: Dict[str, Any], path: Optional[Path] = None) -> Path:
    p = path or (ROOT / "coordination" / "evidence" / "execution_observations" /
                 f"obs_node_{ev['label']}_{ev['started_at'].replace(':', '').replace('-', '')}.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ev, indent=2))
    return p


if __name__ == "__main__":  # pragma: no cover
    import sys
    cmd = sys.argv[1:] or ["npm", "run", "build"]
    ev = observe_node(cmd, label="frontend_build")
    print(json.dumps({k: v for k, v in ev.items()
                      if k not in ("DOES_NOT_OBSERVE", "observes")}, indent=2)[:2500])
    print(f"\nevidence: {write_evidence(ev).relative_to(ROOT)}")
