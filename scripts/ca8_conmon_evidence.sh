#!/usr/bin/env bash
# HELM ConMon (AC8) — verify the continuous-monitoring surface + EMIT fresh NIST 800-53 Rev.5
# evidence under docs/evidence/conmon/.
#
# Evidence-only, per EDR-0005: this NEVER commits, NEVER deploys, NEVER moves money, and
# NEVER touches the frozen runtime. It drives the real continuous loop and re-derives every
# conclusion from artifacts on disk (no fake green — a check it cannot prove FAILS).
#
# Run:  bash scripts/ca8_conmon_evidence.sh
set -uo pipefail
cd "$(dirname "$0")/.."

echo "== 1/3  unit tests: ConMon continuous loop + CA-7 evidence-derived control =="
python3 -m pytest tests/test_conmon_continuous.py tests/test_ca07_evidence_derived.py -q
tests_rc=$?
[ $tests_rc -ne 0 ] && { echo "TESTS FAILED (rc=$tests_rc) — stopping before emitting evidence"; exit $tests_rc; }

echo
echo "== 2/3  drive the CONTINUOUS loop 3 cycles and re-derive continuity from disk =="
python3 scripts/conmon_verify_continuity.py --cycles 3 --interval 2
verify_rc=$?

echo
echo "== 3/3  fresh evidence bundle under docs/evidence/conmon/ =="
ls -1 docs/evidence/conmon/
python3 - <<'PY'
import json, pathlib
ev = pathlib.Path("docs/evidence/conmon")
for name in ("latest.json", "continuity_latest.json"):
    p = ev / name
    if not p.exists():
        print(f"  {name}: MISSING"); continue
    d = json.loads(p.read_text())
    if name == "latest.json":
        print(f"  bundle   : {d.get('posture_percent')}% · {d.get('framework')} · generated {d.get('generated_at')}")
    else:
        verdict = "VERIFIED" if d.get("verified") else "NOT VERIFIED"
        print(f"  continuity: {verdict} · {d.get('cycles')} cycles · {sum(c['passed'] for c in d.get('checks',[]))}/{len(d.get('checks',[]))} checks passed")
PY

echo
if [ $verify_rc -eq 0 ]; then
  echo "AC8 ConMon: continuity VERIFIED, fresh Rev.5 evidence emitted."
else
  echo "AC8 ConMon: continuity NOT verified (rc=$verify_rc) — see the FAIL rows above. No fake green."
fi
exit $verify_rc
