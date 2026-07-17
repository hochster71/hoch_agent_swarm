// test/test_license_gate.js
//
// Proves the license/entitlement gate + policy gate + packaging for the Podcast
// Sting Pack:
//   1) the entitlement gate BLOCKS delivery without an entitlement, ALLOWS with one;
//   2) the LICENSE.txt is generated from the pack's structured terms;
//   3) the policy gate FAILS CLOSED on a seeded vocal-containing track;
//   4) strict mode fails closed when audio is absent (placeholder repo);
//   5) the dependency-free ZIP writer round-trips.
//
// Pure Node, no external test framework. Run: node test/test_license_gate.js

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

let pass = 0, fail = 0;
function ok(name, fn) {
  try { fn(); console.log('  PASS  ' + name); pass++; }
  catch (e) { console.log('  FAIL  ' + name + '  -> ' + e.message); fail++; }
}

const tmpStore = path.join(os.tmpdir(), 'hmf_pod_ent_' + Date.now() + '.json');
const cat = loadCatalog();
const pack = getPack('cold-open', cat);

console.log('HMF Podcast Sting Pack — license-gate + packaging tests\n');

ok('un-entitled buyer is DENIED delivery (fail-closed)', () => {
  let threw = null;
  try { assemblePack(pack, { subject: 'nobody@example.com', storePath: tmpStore, requireAudio: false }); }
  catch (e) { threw = e; }
  assert(threw instanceof DeliveryDenied, 'expected DeliveryDenied');
  assert.strictEqual(threw.code, 'not_entitled');
});

ok('entitled buyer receives a ZIP with LICENSE.txt + manifest.json', () => {
  grantEntitlement('buyer@example.com', { packs: ['cold-open'], source: 'test' }, tmpStore);
  const zip = assemblePack(pack, { subject: 'buyer@example.com', storePath: tmpStore, requireAudio: false });
  assert(Buffer.isBuffer(zip) && zip.length > 0, 'expected non-empty zip buffer');
  assert.strictEqual(zip.readUInt32LE(0), 0x04034b50, 'expected PK local header magic');
  const asText = zip.toString('latin1');
  assert(asText.includes('LICENSE.txt'), 'zip should contain LICENSE.txt');
  assert(asText.includes('manifest.json'), 'zip should contain manifest.json');
});

ok('per-pack entitlement does NOT leak to a different pack', () => {
  // buyer@example.com only bought cold-open; must not get quiet-desk.
  const other = getPack('quiet-desk', cat);
  let threw = null;
  try { assemblePack(other, { subject: 'buyer@example.com', storePath: tmpStore, requireAudio: false }); }
  catch (e) { threw = e; }
  assert(threw instanceof DeliveryDenied && threw.code === 'not_entitled', 'other pack must remain locked');
});

ok('LICENSE.txt is generated from pack license terms', () => {
  const txt = renderLicense(pack, { subject: 'buyer@example.com' });
  assert(txt.includes(pack.license.id), 'license id must appear');
  assert(txt.includes(pack.license.name), 'license name must appear');
  assert(txt.includes(pack.tracks[0].title), 'covered sting title must appear');
  assert(txt.includes('MAY NOT'), 'must include prohibitions section');
  assert(/instrumental/i.test(txt), 'must state instrumental guardrail');
  assert(/PODCAST STING/i.test(txt), 'must be a podcast-sting license');
});

ok('policy gate REJECTS a seeded vocal track (no-vocals guardrail)', () => {
  const seededVocalPack = {
    id: 'seed-bad', title: 'Seeded Bad Pack', tags: { mood: [], genre: [], key: 'C' }, license: pack.license,
    tracks: [{ id: 'bad-01', title: 'Chorus with Lead Vocals', type: 'intro', duration_sec: 8, file: 'x.wav', vocals: true }],
  };
  const res = checkPack(seededVocalPack, {});
  assert.strictEqual(res.pass, false, 'seeded vocal pack must NOT pass');
  assert(res.failures.length === 1, 'exactly one failing track');
  // Entitle the buyer for this pack so GATE 1 (entitlement) passes and it is
  // GATE 2 (policy) that must fail-close on the vocal track.
  grantEntitlement('buyer@example.com', { packs: ['seed-bad'], source: 'test' }, tmpStore);
  let threw = null;
  try { assemblePack(seededVocalPack, { subject: 'buyer@example.com', storePath: tmpStore, requireAudio: false }); }
  catch (e) { threw = e; }
  assert(threw instanceof DeliveryDenied && threw.code === 'policy_failed', 'delivery must fail policy gate');
});

ok('policy gate REJECTS artist-likeness and vocal text markers', () => {
  const r1 = checkTrack({ id: 'a', title: 'Clean Intro', type: 'intro', duration_sec: 8, file: 'a.wav' }, {});
  assert.strictEqual(r1.pass, true, 'clean instrumental should pass');
  const r2 = checkTrack({ id: 'b', title: 'In The Style Of Famous Host', type: 'intro', duration_sec: 8, file: 'b.wav' }, {});
  assert.strictEqual(r2.pass, false, 'style-of-artist title should fail');
  const r3 = checkTrack({ id: 'c', title: 'Intro', type: 'intro', duration_sec: 8, file: 'c.wav', artist_likeness: true }, {});
  assert.strictEqual(r3.pass, false, 'artist_likeness flag should fail');
});

ok('strict mode (requireAudio) fails closed when audio is missing', () => {
  grantEntitlement('buyer2@example.com', { packs: ['cold-open'], source: 'test' }, tmpStore);
  let threw = null;
  try { assemblePack(pack, { subject: 'buyer2@example.com', storePath: tmpStore, requireAudio: true }); }
  catch (e) { threw = e; }
  assert(threw instanceof DeliveryDenied && threw.code === 'policy_failed', 'missing audio must block delivery in strict mode');
});

ok('catalog packs are all available:false (no fabricated audio ships)', () => {
  assert(cat.packs.every((p) => p.available === false), 'placeholder catalog must not mark packs available');
});

ok('zip writer produces a valid End-Of-Central-Directory record', () => {
  const z = buildZip([{ name: 'a.txt', data: 'hello' }, { name: 'b.txt', data: 'world' }]);
  assert.strictEqual(z.readUInt32LE(z.length - 22), 0x06054b50, 'EOCD signature at tail');
  assert.strictEqual(z.readUInt16LE(z.length - 22 + 10), 2, 'EOCD records total = 2');
});

try { fs.unlinkSync(tmpStore); } catch (e) {}

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail === 0 ? 0 : 1);
