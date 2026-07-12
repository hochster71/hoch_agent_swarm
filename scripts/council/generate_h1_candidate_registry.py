"""Build coordination/council/h1_candidate_registry.json — the ONE canonical registry.

Grok F2 required: no filename inference, no last-write-wins, exactly one ACTIVE_CANDIDATE,
disagreement produces EVIDENCE_RECONCILIATION_REQUIRED.

Classification is derived from EVIDENCE INSIDE each package, never from its name:
  - validation.json .authority == NON_RUNTIME_TEST_EVIDENCE      -> NON_EXECUTABLE_TEST_PACKAGE
  - validation.json .status   == NON_EXECUTABLE_TEST_PACKAGE     -> NON_EXECUTABLE_TEST_PACKAGE
  - validation.json .superseded_by is set                        -> SUPERSEDED_BLOCKED_CANDIDATE
  - validation.json .validation_status/.status == BLOCKED        -> SUPERSEDED_BLOCKED_CANDIDATE
  - package fails fresh digest recomputation                     -> SUPERSEDED_BLOCKED_CANDIDATE
  - package has no combined_authorization_sha256 (legacy schema) -> SUPERSEDED_BLOCKED_CANDIDATE
  - exactly one survivor                                         -> ACTIVE_CANDIDATE
  - zero or 2+ survivors                                         -> EVIDENCE_RECONCILIATION_REQUIRED
                                                                    (registry written with
                                                                     authoritative id = null and
                                                                     NOTHING eligible)

The founder-approved authoritative candidate may be pinned via --expect <package_id>;
if the evidence disagrees with the pin, the registry fails reconciliation rather than
silently following either one.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.council.h1_authorization import (  # noqa: E402
    ACTIVE_CANDIDATE,
    EVIDENCE_RECONCILIATION_REQUIRED,
    NON_EXECUTABLE_TEST_PACKAGE,
    PACKAGES_DIR,
    REGISTRY_PATH,
    SUPERSEDED_BLOCKED_CANDIDATE,
    H1AuthorizationValidator,
    _load,
)


def _signed_run_id(pkg: Path) -> str:
    """The run_id inside the SIGNED provider requests.

    This is the strongest available test marker: it lives inside the digest chain, so a
    package cannot shed its TEST identity without breaking combined_authorization_sha256.
    It is package CONTENT, not the directory name -- no filename inference (Grok F2).
    """
    req = _load(pkg / "provider_requests" / "claude.request.redacted.json") or {}
    return str(req.get("run_id") or "")


def classify(package_id: str, packages_dir: Path) -> tuple[str, str]:
    pkg = packages_dir / package_id
    validation = _load(pkg / "validation.json") or {}
    stored = _load(pkg / "request_digests.json") or {}

    authority = str(validation.get("authority") or "")
    status = str(validation.get("status") or validation.get("validation_status") or "")

    if authority == "NON_RUNTIME_TEST_EVIDENCE" or status == NON_EXECUTABLE_TEST_PACKAGE:
        return NON_EXECUTABLE_TEST_PACKAGE, "VALIDATION_EVIDENCE_DECLARES_NON_RUNTIME_TEST"

    run_id = _signed_run_id(pkg)
    if "TEST" in run_id.upper():
        return (
            NON_EXECUTABLE_TEST_PACKAGE,
            f"SIGNED_REQUEST_RUN_ID_IS_TEST_EVIDENCE:{run_id}",
        )

    if validation.get("superseded_by"):
        return (
            SUPERSEDED_BLOCKED_CANDIDATE,
            f"VALIDATION_EVIDENCE_DECLARES_SUPERSEDED_BY:{validation['superseded_by']}",
        )

    if status in ("BLOCKED", SUPERSEDED_BLOCKED_CANDIDATE, "BLOCKED_MODEL_IDENTITY"):
        return SUPERSEDED_BLOCKED_CANDIDATE, f"VALIDATION_EVIDENCE_DECLARES_{status}"

    if not stored.get("combined_authorization_sha256"):
        return (
            SUPERSEDED_BLOCKED_CANDIDATE,
            "LEGACY_SCHEMA_NO_COMBINED_AUTHORIZATION_DIGEST",
        )

    # Fresh recomputation — a package that no longer hashes to its stored chain is dead.
    validator = H1AuthorizationValidator(package_id, packages_dir, registry=None)  # type: ignore[arg-type]
    recomputed = validator.recompute()
    if not recomputed:
        return SUPERSEDED_BLOCKED_CANDIDATE, "INCOMPLETE_PACKAGE"
    recomputed.pop("_requests", None)
    for field, value in recomputed.items():
        if value is not None and stored.get(field) != value:
            return SUPERSEDED_BLOCKED_CANDIDATE, f"PACKAGE_MUTATED_AFTER_REVIEW:{field}"

    return ACTIVE_CANDIDATE, "INTEGRITY_VERIFIED_NOT_SUPERSEDED_NOT_TEST"


def build(packages_dir: Path | None = None, expect: str | None = None) -> dict:
    packages_dir = packages_dir or PACKAGES_DIR
    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    packages = []
    survivors = []
    for package_id in sorted(p.name for p in packages_dir.iterdir() if p.is_dir()):
        classification, reason = classify(package_id, packages_dir)
        if classification == ACTIVE_CANDIDATE:
            survivors.append(package_id)
        packages.append(
            {
                "package_id": package_id,
                "classification": classification,
                "authorization_eligible": False,  # set below, only for the single survivor
                "execution_eligible": False,      # false until the bounded dispatch txn opens
                "reason": reason,
            }
        )

    reconciliation_errors: list[str] = []
    if len(survivors) != 1:
        reconciliation_errors.append(f"EXPECTED_ONE_SURVIVOR_FOUND_{len(survivors)}")
    if expect and survivors and survivors != [expect]:
        reconciliation_errors.append(f"EVIDENCE_DISAGREES_WITH_PINNED_CANDIDATE:{expect}")

    by_id = {p["package_id"]: p for p in packages}

    if reconciliation_errors:
        # Nothing is eligible. Every survivor is demoted; the registry refuses to guess.
        for pid in survivors:
            by_id[pid]["classification"] = SUPERSEDED_BLOCKED_CANDIDATE
            by_id[pid]["reason"] = EVIDENCE_RECONCILIATION_REQUIRED
        return {
            "schema_version": "1.0",
            "generated_at": now,
            "status": EVIDENCE_RECONCILIATION_REQUIRED,
            "reconciliation_errors": reconciliation_errors,
            "authoritative_candidate_package_id": None,
            "candidate_count": 0,
            "packages": packages,
        }

    active = survivors[0]
    by_id[active]["authorization_eligible"] = True

    return {
        "schema_version": "1.0",
        "generated_at": now,
        "status": "RECONCILED",
        "provenance": {
            "derivation": "EVIDENCE_INSIDE_EACH_PACKAGE",
            "filename_inference": False,
            "last_write_wins": False,
            "inputs": [
                "validation.json (.authority, .status, .superseded_by)",
                "request_digests.json (fresh recomputation, not trusted as stored)",
            ],
            "founder_reconciliation": "Michael Bryan Hoch approved this candidate 2026-07-12.",
        },
        "authoritative_candidate_package_id": active,
        "candidate_count": 1,
        "packages": packages,
        "invariants": [
            "exactly one ACTIVE_CANDIDATE",
            "NON_EXECUTABLE_TEST_PACKAGE is never authorization_eligible",
            "SUPERSEDED_BLOCKED_CANDIDATE is never authorization_eligible",
            "execution_eligible is false for every package outside a bounded dispatch transaction",
        ],
    }


def stamp_supersessions(active: str, packages_dir: Path | None = None) -> list[str]:
    """Record supersession as DURABLE EVIDENCE inside each package.

    This is an explicit, attributable reconciliation ACT -- not an inference performed at
    read time. After stamping, build() derives the registry from evidence alone: every
    non-active candidate carries its own superseded_by marker, and if a future package
    ever appears without one, build() refuses with EVIDENCE_RECONCILIATION_REQUIRED
    rather than guessing.
    """
    packages_dir = packages_dir or PACKAGES_DIR
    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    stamped = []
    for pkg_dir in sorted(p for p in packages_dir.iterdir() if p.is_dir()):
        package_id = pkg_dir.name
        if package_id == active:
            continue
        classification, reason = classify(package_id, packages_dir)
        if classification == NON_EXECUTABLE_TEST_PACKAGE:
            continue                     # test packages carry their own marker already
        vpath = pkg_dir / "validation.json"
        doc = _load(vpath) or {}
        if doc.get("superseded_by") == active:
            continue
        doc.update({
            "status": SUPERSEDED_BLOCKED_CANDIDATE,
            "authorization_eligible": False,
            "execution_eligible": False,
            "superseded_by": active,
            "superseded_reason": reason,
            "superseded_at": now,
            "superseded_by_authority": "FOUNDER_RECONCILIATION_2026-07-12",
        })
        vpath.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        stamped.append(package_id)
    return stamped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect", default=None, help="pinned founder-approved package_id")
    ap.add_argument("--stamp", action="store_true",
                    help="write durable supersede markers for every non-active candidate")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.stamp:
        if not args.expect:
            print("--stamp requires --expect <founder-approved package_id>", file=sys.stderr)
            return 2
        stamped = stamp_supersessions(args.expect)
        print(f"stamped superseded: {stamped}", file=sys.stderr)

    doc = build(expect=args.expect)
    if not args.dry_run:
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, indent=2))
    return 0 if doc["status"] == "RECONCILED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
