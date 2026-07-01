# QA Validation Test for Production Hardening Scaffolding
import os
import unittest
import tempfile
import sqlite3
from tls_scaffolding import NGINX_PROXY_TEMPLATE, verify_tls_socket_version
from auth_adapter import OidcAuthAdapter
from audit_ledger_helper import AuditLedgerHelper
from mutation_gate import MutationGate
from observability_scaffolding import JsonStructuredFormatter, PrometheusMetricsExporter
from backup_recovery_scripts import backup_sqlite_database, validate_backup_schema

class TestProductionHardeningScaffolding(unittest.TestCase):

    def test_tls_scaffolding(self):
        self.assertTrue(len(NGINX_PROXY_TEMPLATE) > 100)
        self.assertIn("ssl_protocols TLSv1.3;", NGINX_PROXY_TEMPLATE)
        self.assertTrue(verify_tls_socket_version("TLSv1.3"))
        self.assertFalse(verify_tls_socket_version("TLSv1.2"))

    def test_auth_adapter(self):
        adapter = OidcAuthAdapter(issuer="https://accounts.google.com", client_id="test-client-id")
        claims = adapter.validate_token("valid-operator-token")
        self.assertEqual(claims["sub"], "operator-1")
        self.assertTrue(adapter.enforce_role(claims, ["operator"]))
        self.assertFalse(adapter.enforce_role(claims, ["admin"]))

        with self.assertRaises(ValueError):
            adapter.validate_token("invalid-token")

        # Test JWT parsing validation
        # payload: {"sub": "user-123", "roles": ["operator"], "iss": "https://accounts.google.com"}
        # base64: eyJzdWIiOiAidXNlci0xMjMiLCAicm9sZXMiOiBbIm9wZXJhdG9yIl0sICJpc3MiOiAiaHR0cHM6Ly9hY2NvdW50cy5nb29nbGUuY29tIn0= (padded/unpadded)
        mock_jwt = "header.eyJzdWIiOiAidXNlci0xMjMiLCAicm9sZXMiOiBbIm9wZXJhdG9yIl0sICJpc3MiOiAiaHR0cHM6Ly9hY2NvdW50cy5nb29nbGUuY29tIn0.sig"
        decoded = adapter.validate_token(mock_jwt)
        self.assertEqual(decoded["sub"], "user-123")

    def test_audit_ledger(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db_path = tmp.name
        try:
            helper = AuditLedgerHelper(tmp_db_path)
            uuid_val = helper.record_event("test-actor", "test-action", {"key": "val"})
            self.assertEqual(len(uuid_val), 36) # UUID length

            # Verify local persistence
            conn = sqlite3.connect(tmp_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT actor, action FROM audit_ledger WHERE event_uuid = ?", (uuid_val,))
            row = cursor.fetchone()
            conn.close()

            self.assertIsNotNone(row)
            self.assertEqual(row[0], "test-actor")
            self.assertEqual(row[1], "test-action")
        finally:
            if os.path.exists(tmp_db_path):
                os.remove(tmp_db_path)

    def test_mutation_gate(self):
        gate = MutationGate(verification_endpoint="http://localhost/verify")
        self.assertTrue(gate.authorize_mutation({"mutate": "something"}, "sig-approved-token", nonce="nonce-1"))

        # Replay mutation within same gate with duplicate nonce throws PermissionError
        with self.assertRaises(PermissionError):
            gate.authorize_mutation({"mutate": "something"}, "sig-approved-token", nonce="nonce-1")

        with self.assertRaises(PermissionError):
            gate.authorize_mutation({"mutate": "something"}, "sig-rejected-token", nonce="nonce-2")

        with self.assertRaises(PermissionError):
            gate.authorize_mutation({"mutate": "something"}, "", nonce="nonce-3")

    def test_observability(self):
        exporter = PrometheusMetricsExporter()
        exporter.record_request()
        exporter.record_denial()
        payload = exporter.get_metrics_payload()
        self.assertIn("http_requests_total 1", payload)
        self.assertIn("mutation_gate_denials 1", payload)

    def test_backup_recovery(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp1:
            db1 = tmp1.name
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp2:
            db2 = tmp2.name

        try:
            conn = sqlite3.connect(db1)
            conn.execute("CREATE TABLE t (id INT);")
            conn.commit()
            conn.close()

            success = backup_sqlite_database(db1, db2)
            self.assertTrue(success)
            self.assertTrue(validate_backup_schema(db2))
        finally:
            if os.path.exists(db1):
                os.remove(db1)
            if os.path.exists(db2):
                os.remove(db2)

if __name__ == "__main__":
    unittest.main()
