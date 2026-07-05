/*
 * runtime_truth_status.js
 * UI adapter for the Runtime Truth Contract label-state machine.
 * Mirrors config/runtime_truth_contract.json + docs/doctrine/HAS_EVIDENCE_DISCIPLINE_BASELINE.md.
 *
 * Pure, dependency-free. The dashboard can call labelStateChip(state) to render a
 * status chip. The invariant enforced here: ONLY "VERIFIED" is allowed to render
 * green. Every other state renders in a distinct, non-green class.
 */
(function (root) {
  "use strict";

  var LABEL_STATES = {
    CLAIMED:  { green: false, cssClass: "rt-chip rt-claimed",  label: "CLAIMED",  tone: "muted"  },
    OBSERVED: { green: false, cssClass: "rt-chip rt-observed", label: "OBSERVED", tone: "info"   },
    VERIFIED: { green: true,  cssClass: "rt-chip rt-verified", label: "VERIFIED", tone: "green"  },
    STALE:    { green: false, cssClass: "rt-chip rt-stale",    label: "STALE",    tone: "warn"   },
    UNKNOWN:  { green: false, cssClass: "rt-chip rt-unknown",  label: "UNKNOWN",  tone: "muted"  },
    BLOCKED:  { green: false, cssClass: "rt-chip rt-blocked",  label: "BLOCKED",  tone: "danger" }
  };

  function normalizeState(state) {
    var s = String(state == null ? "UNKNOWN" : state).toUpperCase();
    return LABEL_STATES[s] ? s : "UNKNOWN";
  }

  function labelStateMeta(state) {
    return LABEL_STATES[normalizeState(state)];
  }

  function rendersGreen(state) {
    return labelStateMeta(state).green === true;
  }

  // Given a raw verdict object {status, readiness_score}, decide the chip to show.
  // Fake-green defense: if status says VERIFIED but readiness is at/below the
  // not-ready floor, downgrade the chip to BLOCKED so the UI cannot show green.
  function chipForVerdict(verdict, notReadyCap) {
    notReadyCap = (typeof notReadyCap === "number") ? notReadyCap : 50.0;
    var state = normalizeState(verdict && verdict.status);
    var score = verdict ? Number(verdict.readiness_score) : NaN;
    if (state === "VERIFIED" && !isNaN(score) && score <= notReadyCap) {
      state = "BLOCKED";
    }
    return labelStateMeta(state);
  }

  var api = { LABEL_STATES: LABEL_STATES, normalizeState: normalizeState,
              labelStateMeta: labelStateMeta, rendersGreen: rendersGreen,
              chipForVerdict: chipForVerdict };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.RuntimeTruthStatus = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
