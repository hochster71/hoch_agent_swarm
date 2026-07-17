// engine/motifs.js
//
// HSF — Coloring Book Export — deterministic vector line-art motifs.
//
// Each motif is a function (x, y, w, h) -> string of PDF path operators that
// draw a kid-friendly OUTLINE drawing (stroke only, no fills) inside the box
// whose lower-left corner is (x, y). Colorers fill the shapes in themselves.
//
// Everything is deterministic: same scene -> same motif -> same bytes.
// No external libraries, no randomness, no network.

'use strict';

const K = 0.5523; // circle Bézier kappa

function f(n) { return Number(n.toFixed(2)); }

// Full circle centered (cx,cy) radius r as 4 Bézier curves.
function circle(cx, cy, r) {
  const k = K * r;
  return [
    `${f(cx + r)} ${f(cy)} m`,
    `${f(cx + r)} ${f(cy + k)} ${f(cx + k)} ${f(cy + r)} ${f(cx)} ${f(cy + r)} c`,
    `${f(cx - k)} ${f(cy + r)} ${f(cx - r)} ${f(cy + k)} ${f(cx - r)} ${f(cy)} c`,
    `${f(cx - r)} ${f(cy - k)} ${f(cx - k)} ${f(cy - r)} ${f(cx)} ${f(cy - r)} c`,
    `${f(cx + k)} ${f(cy - r)} ${f(cx + r)} ${f(cy - k)} ${f(cx + r)} ${f(cy)} c`,
    'S',
  ].join('\n');
}

function line(x1, y1, x2, y2) {
  return `${f(x1)} ${f(y1)} m ${f(x2)} ${f(y2)} l S`;
}

function poly(points, close) {
  const parts = [`${f(points[0][0])} ${f(points[0][1])} m`];
  for (let i = 1; i < points.length; i++) parts.push(`${f(points[i][0])} ${f(points[i][1])} l`);
  parts.push(close ? 's' : 'S'); // 's' = closepath + stroke
  return parts.join(' ');
}

function arc(cx, cy, rx, ry, x1, y1, x2, y2) {
  // simple single-curve arch from (x1,y1) to (x2,y2) bulging toward (cx,cy+ry)
  return `${f(x1)} ${f(y1)} m ${f(cx - rx)} ${f(cy + ry)} ${f(cx + rx)} ${f(cy + ry)} ${f(x2)} ${f(y2)} c S`;
}

// ---- motifs (each fills a box x,y,w,h) ------------------------------------

function sun(x, y, w, h) {
  const cx = x + w / 2, cy = y + h / 2, r = Math.min(w, h) * 0.22;
  const out = [circle(cx, cy, r)];
  for (let i = 0; i < 12; i++) {
    const a = (Math.PI * 2 * i) / 12;
    out.push(line(cx + Math.cos(a) * (r + 8), cy + Math.sin(a) * (r + 8),
                  cx + Math.cos(a) * (r + 34), cy + Math.sin(a) * (r + 34)));
  }
  // smiling face
  out.push(circle(cx - r * 0.35, cy + r * 0.25, 4));
  out.push(circle(cx + r * 0.35, cy + r * 0.25, 4));
  out.push(`${f(cx - r * 0.4)} ${f(cy - r * 0.3)} m ${f(cx)} ${f(cy - r * 0.62)} ${f(cx)} ${f(cy - r * 0.62)} ${f(cx + r * 0.4)} ${f(cy - r * 0.3)} c S`);
  // rolling hills below
  out.push(arc(x + w * 0.28, y + 10, w * 0.22, h * 0.16, x, y + 10, x + w * 0.55, y + 10));
  out.push(arc(x + w * 0.75, y + 10, w * 0.2, h * 0.13, x + w * 0.5, y + 10, x + w, y + 10));
  return out.join('\n');
}

function balloons(x, y, w, h) {
  const out = [];
  const specs = [
    [x + w * 0.3, y + h * 0.62, Math.min(w, h) * 0.16],
    [x + w * 0.52, y + h * 0.74, Math.min(w, h) * 0.13],
    [x + w * 0.7, y + h * 0.58, Math.min(w, h) * 0.14],
  ];
  const kx = x + w * 0.5, ky = y + h * 0.08;
  for (const [cx, cy, r] of specs) {
    out.push(circle(cx, cy, r));
    out.push(poly([[cx - 5, cy - r], [cx + 5, cy - r], [cx, cy - r - 8]], true)); // knot
    out.push(`${f(cx)} ${f(cy - r - 8)} m ${f(cx - 10)} ${f((cy + ky) / 2)} ${f(kx + 10)} ${f((cy + ky) / 2)} ${f(kx)} ${f(ky)} c S`); // string
  }
  return out.join('\n');
}

function sailboat(x, y, w, h) {
  const out = [];
  const wl = y + h * 0.3; // waterline
  out.push(poly([[x + w * 0.25, wl], [x + w * 0.75, wl], [x + w * 0.65, wl - h * 0.14], [x + w * 0.35, wl - h * 0.14]], true)); // hull
  out.push(line(x + w * 0.5, wl, x + w * 0.5, wl + h * 0.45)); // mast
  out.push(poly([[x + w * 0.5, wl + h * 0.45], [x + w * 0.5, wl + h * 0.06], [x + w * 0.24, wl + h * 0.06]], true)); // main sail
  out.push(poly([[x + w * 0.54, wl + h * 0.4], [x + w * 0.54, wl + h * 0.06], [x + w * 0.74, wl + h * 0.06]], true)); // jib
  for (let i = 0; i < 3; i++) { // waves
    const wy = wl - h * 0.2 - i * 14;
    out.push(`${f(x + 10)} ${f(wy)} m ${f(x + w * 0.25)} ${f(wy + 10)} ${f(x + w * 0.4)} ${f(wy - 10)} ${f(x + w * 0.55)} ${f(wy)} c ${f(x + w * 0.7)} ${f(wy + 10)} ${f(x + w * 0.85)} ${f(wy - 10)} ${f(x + w - 10)} ${f(wy)} c S`);
  }
  return out.join('\n');
}

function star(x, y, w, h) {
  const cx = x + w / 2, cy = y + h / 2 + h * 0.05, R = Math.min(w, h) * 0.34, r = R * 0.45;
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const rad = i % 2 === 0 ? R : r;
    const a = Math.PI / 2 + (Math.PI * i) / 5;
    pts.push([cx + Math.cos(a) * rad, cy + Math.sin(a) * rad]);
  }
  const out = [poly(pts, true)];
  // little sparkle stars
  for (const [sx, sy] of [[x + w * 0.15, y + h * 0.78], [x + w * 0.85, y + h * 0.72], [x + w * 0.8, y + h * 0.18]]) {
    out.push(line(sx - 8, sy, sx + 8, sy));
    out.push(line(sx, sy - 8, sx, sy + 8));
  }
  return out.join('\n');
}

function mountain(x, y, w, h) {
  const base = y + h * 0.12;
  const out = [];
  out.push(poly([[x + 6, base], [x + w * 0.38, y + h * 0.8], [x + w * 0.62, base]], true));
  out.push(poly([[x + w * 0.45, base], [x + w * 0.72, y + h * 0.68], [x + w - 6, base]], true));
  // snow caps
  out.push(poly([[x + w * 0.31, y + h * 0.62], [x + w * 0.38, y + h * 0.8], [x + w * 0.45, y + h * 0.62], [x + w * 0.41, y + h * 0.66], [x + w * 0.35, y + h * 0.66]], false));
  // moon
  out.push(circle(x + w * 0.84, y + h * 0.84, Math.min(w, h) * 0.09));
  return out.join('\n');
}

function butterfly(x, y, w, h) {
  const cx = x + w / 2, cy = y + h / 2, s = Math.min(w, h);
  const out = [];
  out.push(circle(cx, cy + s * 0.02, s * 0.05)); // head-ish body top
  out.push(`${f(cx)} ${f(cy - s * 0.28)} m ${f(cx)} ${f(cy + s * 0.2)} l S`); // body
  // wings: two big + two small teardrop-ish curves each side
  out.push(`${f(cx)} ${f(cy + s * 0.1)} m ${f(cx - s * 0.45)} ${f(cy + s * 0.42)} ${f(cx - s * 0.45)} ${f(cy - s * 0.02)} ${f(cx)} ${f(cy)} c S`);
  out.push(`${f(cx)} ${f(cy + s * 0.1)} m ${f(cx + s * 0.45)} ${f(cy + s * 0.42)} ${f(cx + s * 0.45)} ${f(cy - s * 0.02)} ${f(cx)} ${f(cy)} c S`);
  out.push(`${f(cx)} ${f(cy - s * 0.05)} m ${f(cx - s * 0.38)} ${f(cy - s * 0.35)} ${f(cx - s * 0.12)} ${f(cy - s * 0.4)} ${f(cx)} ${f(cy - s * 0.15)} c S`);
  out.push(`${f(cx)} ${f(cy - s * 0.05)} m ${f(cx + s * 0.38)} ${f(cy - s * 0.35)} ${f(cx + s * 0.12)} ${f(cy - s * 0.4)} ${f(cx)} ${f(cy - s * 0.15)} c S`);
  // antennae + wing dots to color
  out.push(line(cx - 3, cy + s * 0.3, cx - s * 0.1, cy + s * 0.42));
  out.push(line(cx + 3, cy + s * 0.3, cx + s * 0.1, cy + s * 0.42));
  out.push(circle(cx - s * 0.22, cy + s * 0.16, s * 0.05));
  out.push(circle(cx + s * 0.22, cy + s * 0.16, s * 0.05));
  return out.join('\n');
}

function flowers(x, y, w, h) {
  const out = [];
  const specs = [[x + w * 0.25, 1.0], [x + w * 0.5, 1.25], [x + w * 0.75, 0.9]];
  for (const [cx, scale] of specs) {
    const r = Math.min(w, h) * 0.08 * scale;
    const cy = y + h * 0.55 * scale;
    out.push(circle(cx, cy, r * 0.6)); // center
    for (let i = 0; i < 6; i++) {
      const a = (Math.PI * 2 * i) / 6;
      out.push(circle(cx + Math.cos(a) * r * 1.35, cy + Math.sin(a) * r * 1.35, r * 0.75)); // petals
    }
    out.push(line(cx, cy - r * 2, cx, y + 8)); // stem
    out.push(`${f(cx)} ${f(y + h * 0.16)} m ${f(cx + r)} ${f(y + h * 0.2)} ${f(cx + r * 1.6)} ${f(y + h * 0.12)} ${f(cx + r * 1.2)} ${f(y + h * 0.1)} c S`); // leaf
  }
  return out.join('\n');
}

function rocket(x, y, w, h) {
  const cx = x + w / 2, s = Math.min(w, h);
  const out = [];
  const bodyW = s * 0.18, bodyB = y + h * 0.3, bodyT = y + h * 0.72;
  out.push(poly([[cx - bodyW, bodyB], [cx - bodyW, bodyT], [cx, y + h * 0.9], [cx + bodyW, bodyT], [cx + bodyW, bodyB]], true)); // body + nose
  out.push(circle(cx, (bodyB + bodyT) / 2 + s * 0.03, bodyW * 0.55)); // window
  out.push(poly([[cx - bodyW, bodyB + s * 0.1], [cx - bodyW * 2.1, bodyB - s * 0.04], [cx - bodyW, bodyB]], true)); // left fin
  out.push(poly([[cx + bodyW, bodyB + s * 0.1], [cx + bodyW * 2.1, bodyB - s * 0.04], [cx + bodyW, bodyB]], true)); // right fin
  // flame
  out.push(`${f(cx - bodyW * 0.6)} ${f(bodyB)} m ${f(cx - bodyW * 0.5)} ${f(bodyB - s * 0.16)} ${f(cx)} ${f(bodyB - s * 0.2)} ${f(cx)} ${f(bodyB - s * 0.08)} c ${f(cx)} ${f(bodyB - s * 0.2)} ${f(cx + bodyW * 0.5)} ${f(bodyB - s * 0.16)} ${f(cx + bodyW * 0.6)} ${f(bodyB)} c S`);
  // stars
  for (const [sx, sy] of [[x + w * 0.16, y + h * 0.8], [x + w * 0.85, y + h * 0.6], [x + w * 0.2, y + h * 0.3]]) {
    out.push(line(sx - 7, sy, sx + 7, sy));
    out.push(line(sx, sy - 7, sx, sy + 7));
  }
  return out.join('\n');
}

function house(x, y, w, h) {
  const out = [];
  const hw = w * 0.36, hx = x + w * 0.18, hy = y + h * 0.12, hh = h * 0.4;
  out.push(poly([[hx, hy], [hx, hy + hh], [hx + hw, hy + hh], [hx + hw, hy]], true)); // walls
  out.push(poly([[hx - w * 0.05, hy + hh], [hx + hw / 2, hy + hh + h * 0.24], [hx + hw + w * 0.05, hy + hh]], true)); // roof
  out.push(poly([[hx + hw * 0.4, hy], [hx + hw * 0.4, hy + hh * 0.55], [hx + hw * 0.62, hy + hh * 0.55], [hx + hw * 0.62, hy]], false)); // door
  out.push(circle(hx + hw * 0.58, hy + hh * 0.28, 2.5)); // doorknob
  out.push(poly([[hx + hw * 0.12, hy + hh * 0.6], [hx + hw * 0.12, hy + hh * 0.85], [hx + hw * 0.3, hy + hh * 0.85], [hx + hw * 0.3, hy + hh * 0.6]], true)); // window
  // tree
  const tx = x + w * 0.78, ty = y + h * 0.12;
  out.push(line(tx - 6, ty, tx - 6, ty + h * 0.22));
  out.push(line(tx + 6, ty, tx + 6, ty + h * 0.22));
  out.push(circle(tx, ty + h * 0.38, Math.min(w, h) * 0.16));
  out.push(circle(tx - w * 0.09, ty + h * 0.3, Math.min(w, h) * 0.1));
  out.push(circle(tx + w * 0.09, ty + h * 0.3, Math.min(w, h) * 0.1));
  return out.join('\n');
}

function badge(x, y, w, h) {
  const cx = x + w / 2, cy = y + h / 2, r = Math.min(w, h) * 0.34;
  const out = [circle(cx, cy, r), circle(cx, cy, r * 0.8)];
  // star in the middle
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const rad = i % 2 === 0 ? r * 0.5 : r * 0.22;
    const a = Math.PI / 2 + (Math.PI * i) / 5;
    pts.push([cx + Math.cos(a) * rad, cy + Math.sin(a) * rad]);
  }
  out.push(poly(pts, true));
  // ribbons
  out.push(poly([[cx - r * 0.5, cy - r * 0.9], [cx - r * 0.75, cy - r * 1.6], [cx - r * 0.35, cy - r * 1.45], [cx - r * 0.15, cy - r * 1.0]], true));
  out.push(poly([[cx + r * 0.5, cy - r * 0.9], [cx + r * 0.75, cy - r * 1.6], [cx + r * 0.35, cy - r * 1.45], [cx + r * 0.15, cy - r * 1.0]], true));
  return out.join('\n');
}

function cloudsAndKite(x, y, w, h) {
  const out = [];
  for (const [cx, cy, s] of [[x + w * 0.28, y + h * 0.78, 1], [x + w * 0.7, y + h * 0.66, 0.8]]) {
    const r = Math.min(w, h) * 0.09 * s;
    out.push(circle(cx - r * 1.4, cy, r));
    out.push(circle(cx, cy + r * 0.5, r * 1.2));
    out.push(circle(cx + r * 1.5, cy, r));
    out.push(line(cx - r * 2.2, cy - r * 0.8, cx + r * 2.3, cy - r * 0.8));
  }
  // kite
  const kx = x + w * 0.5, ky = y + h * 0.34, kw = w * 0.12, kh = h * 0.16;
  out.push(poly([[kx, ky + kh], [kx + kw, ky], [kx, ky - kh], [kx - kw, ky]], true));
  out.push(line(kx - kw, ky, kx + kw, ky));
  out.push(line(kx, ky + kh, kx, ky - kh));
  out.push(`${f(kx)} ${f(ky - kh)} m ${f(kx - w * 0.1)} ${f(y + h * 0.14)} ${f(kx + w * 0.08)} ${f(y + h * 0.1)} ${f(kx - w * 0.04)} ${f(y + 8)} c S`); // tail
  return out.join('\n');
}

// Kicker -> motif mapping (deterministic; mirrors the story arc built by the
// vendored story engine). Fallback hashes the heading so unknown kickers still
// get a stable drawing.
const MOTIFS = [sun, balloons, sailboat, star, mountain, butterfly, flowers, rocket, house, badge, cloudsAndKite];

const KICKER_MAP = [
  [/^prologue/i, sun],
  [/^the call/i, balloons],
  [/^the journey/i, sailboat],
  [/^turning point/i, star],
  [/^the struggle/i, mountain],
  [/^the doctrine/i, butterfly],
  [/^the recovery/i, flowers],
  [/^the next launch/i, rocket],
  [/^mission patch/i, badge],
];

function hashStr(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
  return h >>> 0;
}

function motifForScene(scene, index) {
  const kicker = String(scene.kicker || '');
  for (const [re, fn] of KICKER_MAP) if (re.test(kicker)) return fn;
  const key = kicker + '|' + String(scene.heading || '') + '|' + index;
  return MOTIFS[hashStr(key) % MOTIFS.length];
}

module.exports = { motifForScene, MOTIFS, cover: cloudsAndKite, backCover: badge };
