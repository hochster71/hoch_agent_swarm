"""The secret scanner must grade JWTs by decoded claims, not blanket-HIGH every `eyJ...`.

Evidence discipline cuts both ways: a false-HIGH (demo/anon key mislabeled a leak) is as much a
fake-signal as a false-GREEN. This locks in the Epic-Fury correction — demo keys and public anon keys
grade LOW; only a real privileged (service_role) JWT grades HIGH.

All tokens are assembled at runtime from claim dicts, so no literal JWT enters HOCH source.
"""
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from backend.swarm.cyber_swarm import _classify_jwt, scan_secrets  # noqa: E402


def _jwt(claims: dict) -> str:
    seg = lambda o: base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip("=")
    return seg({"alg": "HS256", "typ": "JWT"}) + "." + seg(claims) + "." + ("s" * 43)


def test_demo_service_role_is_low():
    g = _classify_jwt(_jwt({"iss": "supabase-demo", "role": "service_role", "exp": 1983812996}))
    assert g["severity"] == "LOW"  # public demo default, not a real secret


def test_anon_key_is_low():
    g = _classify_jwt(_jwt({"iss": "supabase", "ref": "abc123", "role": "anon"}))
    assert g["severity"] == "LOW"  # anon is public by design (RLS-gated)


def test_real_service_role_is_high():
    g = _classify_jwt(_jwt({"iss": "supabase", "ref": "realproj", "role": "service_role"}))
    assert g["severity"] == "HIGH"  # privileged credential from a real issuer = true leak


def test_opaque_jwt_stays_high():
    # a non-decodable token (seeded-fault style) must stay HIGH — conservative default
    assert _classify_jwt("eyJx.notbase64json.sig")["severity"] == "HIGH"


def test_scan_grades_demo_compose_low_and_keeps_category(tmp_path):
    (tmp_path / "docker-compose.yml").write_text(
        "environment:\n  SERVICE_KEY: " + _jwt({"iss": "supabase-demo", "role": "service_role"}) + "\n")
    hits = [h for h in scan_secrets(tmp_path) if h["category"] == "JWT_OR_SUPABASE"]
    assert len(hits) == 1
    assert hits[0]["severity"] == "LOW"          # no longer a false HIGH
    assert hits[0]["category"] == "JWT_OR_SUPABASE"  # purple coverage keys on category — unchanged


def test_scan_flags_real_service_role_high(tmp_path):
    (tmp_path / "leak.ts").write_text("const k = '" + _jwt({"iss": "supabase", "role": "service_role"}) + "'\n")
    hits = [h for h in scan_secrets(tmp_path) if h["category"] == "JWT_OR_SUPABASE"]
    assert hits and hits[0]["severity"] == "HIGH"


if __name__ == "__main__":
    import tempfile, traceback
    fns = [(n, f) for n, f in dict(globals()).items() if n.startswith("test_")]
    fails = 0
    for n, f in fns:
        try:
            if f.__code__.co_argcount:
                with tempfile.TemporaryDirectory() as d:
                    f(Path(d))
            else:
                f()
            print("PASS", n)
        except Exception:
            fails += 1; print("FAIL", n); traceback.print_exc()
    print(f"--- {len(fns)-fails}/{len(fns)} passed")
    sys.exit(1 if fails else 0)
