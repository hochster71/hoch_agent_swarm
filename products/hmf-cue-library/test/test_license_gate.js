// test/test_license_gate.js
//
// Proves the two things the spec demands:
//   1) the license/entitlement gate BLOCKS delivery without an entitlement,
//      and ALLOWS it with one (fail-closed);
//   2) the LICENSE.txt is generated from the pack's structured terms;
//   3) the policy gate FAILS CLOSED on a seeded vocal-containing track.
//
// Pure Node, no external test framework. Run: node test/test_license_gate.js
// Uses a temp entitlement store so it never touches real data.

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');

const { loadCatalog, getPack } = require('../engine/catalog');
const { grantEntitlement } = require('../engine/entitlements');
const { assemblePack, DeliveryDenied } = require('../engine/packager');
const { checkPack, checkTrack } = require('../engine/gate');
const { renderLicense } = require('../engine/license');
const { buildZip } = require('../engine/zip');

let pass = 0;
let fail = 0;
function ok(name, fn) {
  try { fn(); console.log('  PASS  ' + name); pass++; }
  catch (e) { console.log('  FAIL  ' + name + '  -> ' + e.message); fail++; }
}

const tmpStore = path.join(os.tmpdir(), 'hmf_ent_' + Date.now() + '.json');
const cat = loadCatalog();
const pack = getPack('midnight-drive', cat);

console.log('HMF Cue Library — license-gate + packaging tests\n');

// --- 1. Gate BLOCKS with no entitlement ---
ok('un-entitled buyer is DENIED delivery (fail-closed)', () => {
  let threw = null;
  try {
    assemblePack(pack, { subject: 'nobody@example.com', storePath: tmpStore, requireAudio: false });
  } catch (e) { threw = e; }
  assert(threw instanceof DeliveryDenied, 'expected DeliveryDenied');
  assert.strictEqual(threw.code, 'not_entitled', 'expected not_entitled, got ' + (threw && threw.code));
});

// --- 2. Gate ALLOWS after entitlement granted (placeholder mode) ---
ok('entitled buyer receives a ZIP with LICENSE.txt + manifest.json', () => {
  grantEntitlement('buyer@example.com', { packs: '*', source: 'test' }, tmpStore);
  const zip = assemblePack(pack, { subject: 'buyer@example.com', storePath: tmpStore, requireAudio: false });
  assert(Buffer.isBuffer(zip) && zip.length > 0, 'expected non-empty zip buffer');
  // ZIP magic + central-dir contains our filenames
  assert.strictEqual(zip.readUInt32LE(0), 0x04034b50, 'expected PK local header magic');
  const asText = zip.toString('latin1');
  assert(asText.includes('LICENSE.txt'), 'zip should contain LICENSE.txt');
  assert(asText.includes('manifest.json'), 'zip should contain manifest.json');
});

// --- 3. LICENSE.txt is derived from the pack's structured terms ---
ok('LICENSE.txt is generated from pack license terms', () => {
  const txt = renderLicense(pack, { subject: 'buyer@example.com' });
  assert(txt.includes(pack.license.id), 'license id must appear');
  assert(txt.includes(pack.license.name), 'license name must appear');
  assert(txt.includes(pack.tracks[0].title), 'covered track title must appear');
  // prohibitions from catalog must be reflected
  assert(txt.includes('MAY NOT'), 'must include prohibitions section');
  assert(/instrumental/i.test(txt), 'must state instrumental guardrail');
});

// --- 4. Policy gate FAILS CLOSED on a seeded vocal-containing track ---
ok('policy gate REJECTS a seeded vocal track (no-vocals guardrail)', () => {
  const seededVocalPack = {
    id: 'seed-bad',
    title: 'Seeded Bad Pack',
    tags: { mood: [], genre: [], key: 'C' },
    license: pack.license,
    tracks: [
      { id: 'bad-01', title: 'Chorus with Lead Vocals', type: 'bed', duration_sec: 60, file: 'x.wav', vocals: true },
    ],
  };
  const res = checkPack(seededVocalPack, {});
  assert.strictEqual(res.pass, false, 'seeded vocal pack must NOT pass');
  assert(res.failures.length === 1, 'exactly one failing track');
  // and delivery must be refused even for an entitled buyer
  let threw = null;
  try {
    assemblePack(seededVocalPack, { subject: 'buyer@example.com', storePath: tmpStore, requireAudio: false });
  } catch (e) { threw = e; }
  assert(threw instanceof DeliveryDenied && threw.code === 'policy_failed', 'delivery must fail policy gate');
});

// --- 5. Policy gate catches artist-likeness + text markers ---
ok('policy gate REJECTS artist-likeness and vocal text markers', () => {
  const r1 = checkTrack({ id: 'a', title: 'Clean Bed', type: 'bed', duration_sec: 30, file: 'a.wav' }, {});
  assert.strictEqual(r1.pass, true, 'clean instrumental should pass');
  const r2 = checkTrack({ id: 'b', title: 'In The Style Of Famous Singer', type: 'bed', duration_sec: 30, file: 'b.wav' }, {});
  assert.strictEqual(r2.pass, false, 'style-of-artist title should fail');
  const r3 = checkTrack({ id: 'c', title: 'Bed', type: 'bed', duration_sec: 30, file: 'c.wav', artist_likeness: true }, {});
  assert.strictEqual(r3.pass, false, 'artist_likeness flag should fail');
});

// --- 6. requireAudio=true fails closed when files are absent (placeholder repo) ---
ok('strict mode (requireAudio) fails closed when audio is missing', () => {
  grantEntitlement('buyer2@example.com', { packs: ['midnight-drive'], source: 'test' }, tmpStore);
  let threw = null;
  try {
    assemblePack(pack, { subject: 'buyer2@example.com', storePath: tmpStore, requireAudio: true });
  } catch (e) { threw = e; }
  assert(threw instanceof DeliveryDenied && threw.code === 'policy_failed',
    'missing audio must block delivery in strict mode');
});

// --- 7. ZIP writer round-trips (structural sanity) ---
ok('zip writer produces a valid End-Of-Central-Directory record', () => {
  const z = buildZip([{ name: 'a.txt', data: 'hello' }, { name: 'b.txt', data: 'world' }]);
  assert.strictEqual(z.readUInt32LE(z.length - 22), 0x06054b50, 'EOCD signature at tail');
  assert.strictEqual(z.readUInt16LE(z.length - 22 + 10), 2, 'EOCD records total = 2');
});

try { fs.unlinkSync(tmpStore); } catch (e) {}

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail === 0 ? 0 : 1);
