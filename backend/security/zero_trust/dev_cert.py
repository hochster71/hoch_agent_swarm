"""Self-signed DEV TLS cert generation for staged TLS termination (SC-8).

The running service is plain HTTP. Adding TLS is a cutover-only change. This module
generates a *development* self-signed cert into a GITIGNORED directory so the
private key is never committed. It is used by the staged launcher and by the tests
to prove a cert loads into an ``ssl.SSLContext``.

Nothing here touches the network or the running server. It only writes files under
``_dev_certs/`` (which carries its own ``.gitignore`` that excludes every key/cert).
"""

from __future__ import annotations

import datetime
import ipaddress
import ssl
from pathlib import Path
from typing import Tuple

# Keep all TLS key material OUTSIDE the repository tree entirely — never inside a
# scanned source dir (backend/scripts/config/tests/frontend/deploy). A private key
# at rest under backend/ trips the literal-secret scanner and is a real finding,
# even if gitignored. ~/.helm/dev_certs is outside the repo, outside git, unscanned.
CERT_DIR = Path.home() / ".helm" / "dev_certs"
CERT_PATH = CERT_DIR / "helm_dev_cert.pem"
KEY_PATH = CERT_DIR / "helm_dev_key.pem"

# Directory-local gitignore so private keys can NEVER be committed even if the root
# .gitignore is edited by another agent. Belt and suspenders.
_GITIGNORE = "# staged dev TLS material — never commit\n*\n!.gitignore\n"


def _ensure_dir() -> None:
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    gi = CERT_DIR / ".gitignore"
    if not gi.exists():
        gi.write_text(_GITIGNORE)


def generate_dev_cert(
    cert_path: Path = CERT_PATH,
    key_path: Path = KEY_PATH,
    *,
    common_name: str = "helm.local",
    days_valid: int = 365,
    overwrite: bool = False,
) -> Tuple[Path, Path]:
    """Generate a self-signed cert+key for localhost / loopback. Returns (cert, key).

    Idempotent: if both files exist and ``overwrite`` is False, returns them as-is.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    _ensure_dir()
    if cert_path.exists() and key_path.exists() and not overwrite:
        return cert_path, key_path

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "HELM DEV (self-signed)"),
        ]
    )
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=days_valid))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.DNSName(common_name),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                    x509.IPAddress(ipaddress.IPv6Address("::1")),
                ]
            ),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    # Private key: owner-only perms, gitignored dir. Never committed.
    key_bytes = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_path.write_bytes(key_bytes)
    try:
        key_path.chmod(0o600)
    except OSError:
        pass
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert_path, key_path


def load_ssl_context(
    cert_path: Path = CERT_PATH, key_path: Path = KEY_PATH
) -> ssl.SSLContext:
    """Build a server-side SSLContext from the dev cert. Generates it if absent.

    Proves (in tests) that the staged TLS material is loadable without ever binding
    a socket.
    """
    if not (cert_path.exists() and key_path.exists()):
        generate_dev_cert(cert_path, key_path)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
    return ctx


if __name__ == "__main__":
    c, k = generate_dev_cert()
    print(f"dev cert: {c}")
    print(f"dev key : {k} (gitignored, mode 600)")
