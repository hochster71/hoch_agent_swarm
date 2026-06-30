#!/usr/bin/env bash
# transport_security_check.sh - Audits HTTP redirect and HTTP security headers

set -euo pipefail

echo "==> Running Transport Security Compliance Audit..."

# 1. Verify HTTP-to-HTTPS redirect
echo "Checking HTTP redirect behavior..."
redirect_headers=$(curl -sI --resolve has.localhost:80:127.0.0.1 http://has.localhost/)
if ! echo "$redirect_headers" | grep -Ei "Location: https://has.localhost" >/dev/null; then
  echo "❌ FAIL: HTTP requests did not redirect to HTTPS!"
  exit 1
fi
echo "  [OK] Redirect to HTTPS validated."

# 2. Verify Secure Transport Headers on HTTPS response
echo "Fetching HTTPS response headers..."
headers=$(curl -sI -k --resolve has.localhost:443:127.0.0.1 https://has.localhost/)

# Convert headers to lowercase for easy matching
headers_lower=$(echo "$headers" | tr '[:upper:]' '[:lower:]')

# Check Strict-Transport-Security
if ! echo "$headers_lower" | grep -Fi "strict-transport-security" >/dev/null; then
  echo "❌ FAIL: Strict-Transport-Security header is missing!"
  exit 1
fi
echo "  [OK] Strict-Transport-Security present."

# Check X-Frame-Options
if ! echo "$headers_lower" | grep -Fi "x-frame-options: deny" >/dev/null; then
  echo "❌ FAIL: X-Frame-Options must be strictly set to 'deny'!"
  exit 1
fi
echo "  [OK] X-Frame-Options present and set to 'deny'."

# Check X-Content-Type-Options
if ! echo "$headers_lower" | grep -Fi "x-content-type-options: nosniff" >/dev/null; then
  echo "❌ FAIL: X-Content-Type-Options must be set to 'nosniff'!"
  exit 1
fi
echo "  [OK] X-Content-Type-Options present and set to 'nosniff'."

# Check Content-Security-Policy
if ! echo "$headers_lower" | grep -Fi "content-security-policy" >/dev/null; then
  echo "❌ FAIL: Content-Security-Policy header is missing!"
  exit 1
fi
echo "  [OK] Content-Security-Policy present."

echo "[PASS] Transport security audit successfully passed."
exit 0
