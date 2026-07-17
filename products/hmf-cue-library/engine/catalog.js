// engine/catalog.js
//
// HMF Cue Library — catalog data model + loader.
//
// The catalog is driven by catalog/catalog.json (a JSON manifest). This module
// loads, validates, and exposes two views:
//   * publicView()  -> metadata + previews ONLY (safe for un-entitled users)
//   * getPack(id)   -> full pack record incl. track file paths (server-side only,
//                       used AFTER an entitlement check by the delivery path)
//
// It never reads or serves audio bytes itself — delivery is the packager's job,
// and only after the license-gate says yes.

'use strict';

const fs = require('fs');
const path = require('path');

const CATALOG_PATH = path.join(__dirname, '..', 'catalog', 'catalog.json');

function loadCatalog(catalogPath) {
  const p = catalogPath || CATALOG_PATH;
  const raw = fs.readFileSync(p, 'utf8');
  const cat = JSON.parse(raw);
  validateCatalog(cat);
  return cat;
}

// Fail-closed validation: a malformed catalog must not silently serve.
function validateCatalog(cat) {
  if (!cat || typeof cat !== 'object') throw new Error('catalog: not an object');
  if (!Array.isArray(cat.packs)) throw new Error('catalog: missing packs[]');
  const seen = new Set();
  for (const pack of cat.packs) {
    for (const field of ['id', 'title', 'tags', 'tracks', 'license']) {
      if (!(field in pack)) throw new Error(`catalog: pack missing "${field}"`);
    }
    if (seen.has(pack.id)) throw new Error(`catalog: duplicate pack id "${pack.id}"`);
    seen.add(pack.id);
    if (!Array.isArray(pack.tracks) || pack.tracks.length === 0) {
      throw new Error(`catalog: pack "${pack.id}" has no tracks`);
    }
    for (const t of pack.tracks) {
      for (const field of ['id', 'title', 'file', 'duration_sec']) {
        if (!(field in t)) throw new Error(`catalog: track in "${pack.id}" missing "${field}"`);
      }
    }
    for (const field of ['id', 'name', 'grant']) {
      if (!(field in pack.license)) throw new Error(`catalog: pack "${pack.id}" license missing "${field}"`);
    }
  }
  return true;
}

// Strip everything an un-entitled visitor must not receive: real file paths.
// Keep title/tags/track metadata (title, duration, bpm, key, type) as previews.
function toPreviewPack(pack) {
  return {
    id: pack.id,
    title: pack.title,
    blurb: pack.blurb || '',
    available: !!pack.available,
    price_note: pack.price_note || '',
    tags: pack.tags,
    track_count: pack.tracks.length,
    total_duration_sec: pack.tracks.reduce((s, t) => s + (t.duration_sec || 0), 0),
    tracks: pack.tracks.map((t) => ({
      id: t.id,
      title: t.title,
      type: t.type,
      duration_sec: t.duration_sec,
      bpm: t.bpm,
      key: t.key,
      // NOTE: no "file" field — un-entitled users never learn the delivery path.
    })),
    license: {
      id: pack.license.id,
      name: pack.license.name,
      attribution_required: !!pack.license.attribution_required,
    },
  };
}

function publicView(catalog) {
  const cat = catalog || loadCatalog();
  return {
    catalog_version: cat.catalog_version,
    status: cat.status,
    guardrail: cat.guardrail,
    honesty_note: cat.honesty_note,
    packs: cat.packs.map(toPreviewPack),
  };
}

function getPack(id, catalog) {
  const cat = catalog || loadCatalog();
  return cat.packs.find((p) => p.id === id) || null;
}

module.exports = { loadCatalog, validateCatalog, publicView, getPack, toPreviewPack, CATALOG_PATH };
