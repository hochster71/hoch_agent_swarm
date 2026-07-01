#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/hoch-drogon-tv"
BACKEND_DIR="$APP_DIR/backend"

mkdir -p "$BACKEND_DIR"
cd "$BACKEND_DIR"

cat > package.json <<'JSON'
{
  "name": "hoch-drogon-tv-login",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "login:test": "node login-test.js"
  },
  "dependencies": {
    "dotenv": "latest"
  }
}
JSON

cat > .env.example <<'ENV'
DROGON_SERVER_URL="http://YOUR_PORTAL_URL_HERE"
DROGON_USERNAME="michaelhoch"
DROGON_PASSWORD="YOUR_PASSWORD_HERE"
PORT=8787
ENV

if [ ! -f .env ]; then
  cp .env.example .env
fi

cat > login-test.js <<'JS'
import dotenv from "dotenv";

dotenv.config();

const {
  DROGON_SERVER_URL,
  DROGON_USERNAME = "michaelhoch",
  DROGON_PASSWORD
} = process.env;

function fail(message) {
  console.error(`\n[FAIL] ${message}\n`);
  process.exit(1);
}

if (!DROGON_SERVER_URL || DROGON_SERVER_URL.includes("YOUR_PORTAL_URL")) {
  fail("Set DROGON_SERVER_URL in .env.");
}

if (!DROGON_PASSWORD || DROGON_PASSWORD.includes("YOUR_PASSWORD")) {
  fail("Set DROGON_PASSWORD in .env.");
}

function buildUrl(action = null) {
  const url = new URL("/player_api.php", DROGON_SERVER_URL);
  url.searchParams.set("username", DROGON_USERNAME);
  url.searchParams.set("password", DROGON_PASSWORD);
  if (action) url.searchParams.set("action", action);
  return url;
}

async function fetchJson(url) {
  const res = await fetch(url);
  const text = await res.text();

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`);
  }

  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Non-JSON response: ${text.slice(0, 240)}`);
  }
}

async function main() {
  console.log("\n[HOCH DROGON LOGIN TEST]");
  console.log(`Server: ${DROGON_SERVER_URL}`);
  console.log(`Username: ${DROGON_USERNAME}`);
  console.log("Password: ********");

  const account = await fetchJson(buildUrl());
  const user = account.user_info || {};

  console.log("\n[ACCOUNT]");
  console.log(`Status: ${user.status || "unknown"}`);
  console.log(`Auth: ${user.auth ?? "unknown"}`);
  console.log(`Active connections: ${user.active_cons || "unknown"}`);
  console.log(`Max connections: ${user.max_connections || "unknown"}`);
  console.log(`Expires: ${user.exp_date || "unknown"}`);

  const categories = await fetchJson(buildUrl("get_live_categories"));
  console.log("\n[LIVE CATEGORIES]");
  console.log(`Count: ${Array.isArray(categories) ? categories.length : "unknown"}`);

  const streams = await fetchJson(buildUrl("get_live_streams"));
  console.log("\n[LIVE STREAMS]");
  console.log(`Count: ${Array.isArray(streams) ? streams.length : "unknown"}`);

  console.log("\n[PASS] Drogon.TV login works.\n");
}

main().catch(err => fail(err.message));
JS

npm install

echo ""
echo "[DONE] Created $APP_DIR"
echo "Next:"
echo "  nano $BACKEND_DIR/.env"
echo "  cd $BACKEND_DIR && npm run login:test"
echo ""
