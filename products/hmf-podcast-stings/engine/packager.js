// engine/packager.js
//
// HMF — Podcast Sting Pack — pack assembly + gated delivery.
//
// assemblePack(pack, opts) returns a ZIP Buffer containing:
//   * each sting's audio file (only when real files exist and pass the policy gate)
//   * LICENSE.txt   (generated from the pack's structured license terms)
//   * manifest.json (per-sting: title, duration, bpm, key, license id)
//
// TWO gates run before any bytes are assembled:
//   1) entitlement gate (isEntitled) — buyer must have paid.
//   2) policy gate (checkPack) — every sting must be instrumental / no-likeness,
//      and (in strict/real mode) present + non-empty.
// If either fails, assemblePack THROWS — fail-closed, nothing is delivered.

'use strict';

const fs = require('fs');
const path = require('path');
const { buildZip } = require('./zip');
const { renderLicense } = require('./license');
const { checkPack } = require('./gate');
const { isEntitled } = require('./entitlements');

class DeliveryDenied extends Error {
  constructor(message, code) {
    super(message);
    this.name = 'DeliveryDenied';
    this.code = code || 'denied';
  }
}

function buildManifest(pack, nowIso) {
  return {
    pack_id: pack.id,
    title: pack.title,
    generated_utc: nowIso,
    license_id: pack.license.id,
    tags: pack.tags,
    tracks: pack.tracks.map((t) => ({
      id: t.id,
      title: t.title,
      type: t.type,
      duration_sec: t.duration_sec,
      bpm: t.bpm,
      key: t.key,
      file: path.basename(t.file),
      license_id: pack.license.id,
    })),
  };
}

function assemblePack(pack, opts) {
  const o = opts || {};
  const nowIso = o.nowIso || new Date().toISOString();

  // --- GATE 1: entitlement (purchase) ---
  if (!isEntitled(o.subject, pack.id, o.storePath)) {
    throw new DeliveryDenied(
      `No active entitlement for subject "${o.subject}" on pack "${pack.id}".`,
      'not_entitled'
    );
  }

  // --- GATE 2: policy (instrumental / no-likeness, + file presence if strict) ---
  const requireAudio = o.requireAudio === true;
  const policy = checkPack(pack, { requireFile: requireAudio, baseDir: o.baseDir || path.join(__dirname, '..') });
  if (!policy.pass) {
    throw new DeliveryDenied(
      `Policy gate failed for pack "${pack.id}": ` +
        policy.failures.map((f) => `${f.id}[${f.reasons.join('; ')}]`).join(', '),
      'policy_failed'
    );
  }

  // --- assemble ---
  const files = [];
  const manifest = buildManifest(pack, nowIso);
  files.push({ name: 'manifest.json', data: JSON.stringify(manifest, null, 2) });
  files.push({ name: 'LICENSE.txt', data: renderLicense(pack, { nowIso, subject: o.subject }) });

  if (requireAudio) {
    const baseDir = o.baseDir || path.join(__dirname, '..');
    for (const t of pack.tracks) {
      const abs = path.join(baseDir, t.file);
      files.push({ name: path.basename(t.file), data: fs.readFileSync(abs) });
    }
  } else {
    // Placeholder mode: no real audio exists yet. Ship an honest note instead of
    // fake tones so the archive is never mistaken for a real deliverable.
    files.push({
      name: 'README_NO_AUDIO.txt',
      data:
        'This archive was assembled in PLACEHOLDER mode — no real audio exists yet.\n' +
        'The license gate and packaging are REAL and were exercised, but the founder\n' +
        'must drop license-cleared, instrumental-only stings into stings/' + pack.id + '/\n' +
        'and re-run with requireAudio=true before selling. See product README.\n',
    });
  }

  return buildZip(files);
}

module.exports = { assemblePack, buildManifest, DeliveryDenied };
