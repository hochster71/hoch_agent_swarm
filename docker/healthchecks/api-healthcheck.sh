#!/usr/bin/env bash
set -euo pipefail

curl -fsS http://127.0.0.1:8000/api/v1/runtime-truth/state > /dev/null
