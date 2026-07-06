"""Guard-the-guard: the version-controlled pre-commit hook must block a committed Supabase/JWT secret.

This is the recurrence guard the Epic-Fury rotation runbook calls for (docs/runbooks/
epic-fury-secret-rotation.md). It runs the ACTUAL hook (scripts/git-hooks/pre-commit) in a throwaway
git repo. The fake service_role JWT is assembled at runtime from parts so no literal 3-part `eyJ` token
ever exists in HOCH source (keeps the no-literal-secrets scanner clean).
"""
import base64
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = ROOT / "scripts" / "git-hooks" / "pre-commit"


def _b64url(obj) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")


def _fake_service_role_jwt() -> str:
    # Structurally a signed JWT (header.payload.signature) but assembled here — never a source literal.
    header = _b64url({"alg": "HS256", "typ": "JWT"})
    payload = _b64url({"role": "service_role", "iss": "supabase", "iat": 1000000000})
    sig = "s" * 43  # opaque signature segment
    return header + "." + payload + "." + sig


def _run_hook_in_temp_repo(tmp: Path, filename: str, content: str) -> subprocess.CompletedProcess:
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp, check=True)
    (tmp / filename).write_text(content)
    subprocess.run(["git", "add", filename], cwd=tmp, check=True)
    return subprocess.run(["bash", str(HOOK)], cwd=tmp, capture_output=True, text=True)


def test_hook_blocks_supabase_service_role_jwt(tmp_path):
    r = _run_hook_in_temp_repo(tmp_path, "docker-compose.yml",
                               "environment:\n  SERVICE_ROLE_KEY: " + _fake_service_role_jwt() + "\n")
    assert r.returncode == 1, "hook should FAIL-CLOSED on a committed signed JWT"
    assert "signed JWT" in r.stdout


def test_hook_allows_clean_file(tmp_path):
    r = _run_hook_in_temp_repo(tmp_path, "config.yaml", "environment:\n  LOG_LEVEL: info\n")
    assert r.returncode == 0, "hook should pass a file with no secret"


def test_hook_still_blocks_stripe_live_key(tmp_path):
    key = "sk_" + "live_" + "A" * 24  # assembled, not a literal
    r = _run_hook_in_temp_repo(tmp_path, "settings.json", '{"stripe": "' + key + '"}\n')
    assert r.returncode == 1
    assert "Stripe" in r.stdout


def test_hook_skips_test_fixtures(tmp_path):
    # test files legitimately carry fixture secrets; hook must not block them
    r = _run_hook_in_temp_repo(tmp_path, "test_x.py", "TOKEN = '" + _fake_service_role_jwt() + "'\n")
    assert r.returncode == 0


def test_versioned_and_live_hook_agree():
    live = ROOT / ".git" / "hooks" / "pre-commit"
    if live.exists():  # skip gracefully off a full checkout
        assert "signed JWT" in live.read_text(), "live hook is stale — run scripts/install_git_hooks.sh"


if __name__ == "__main__":
    import tempfile
    fails = 0
    fns = [(n, f) for n, f in globals().items() if n.startswith("test_")]
    for n, f in fns:
        try:
            if "tmp_path" in f.__code__.co_varnames[: f.__code__.co_argcount]:
                with tempfile.TemporaryDirectory() as d:
                    f(Path(d))
            else:
                f()
            print("PASS", n)
        except Exception as e:
            fails += 1
            print("FAIL", n, "::", e)
    print(f"--- {len(fns)-fails}/{len(fns)} passed")
    sys.exit(1 if fails else 0)
