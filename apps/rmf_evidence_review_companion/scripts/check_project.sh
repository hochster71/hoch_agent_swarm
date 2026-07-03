#!/usr/bin/env bash
# Verifies project integrity
set -e

if [ ! -f "pubspec.yaml" ]; then
  echo "[error] pubspec.yaml missing."
  exit 1
fi

echo "[success] Scaffold check passed."
exit 0
