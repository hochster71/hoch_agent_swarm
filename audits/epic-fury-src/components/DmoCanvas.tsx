'use client'

// ═══════════════════════════════════════════════════════════════════════════════
//  DMO CANVAS — NTDS/AEGIS + JADC2 JICO ENVIRONMENT
//  MIL-STD-2525 track symbology · Real geo projection · Link-16 animation
// ═══════════════════════════════════════════════════════════════════════════════

import { useEffect, useRef, useState, useCallback } from 'react'
import { Play, Pause, RotateCcw, Radio, Crosshair } from 'lucide-react'
import { getConflictDay, toDTG } from '@/lib/conflict-day'

// ── Map projection  LON 54.5–59.0°E  ×  LAT 24.8–28.2°N ──────────────────────
const LON0 = 54.5, LON1 = 59.0
const LAT0 = 24.8, LAT1 = 28.2
function geoX(lon: number, w: number) { return ((lon - LON0) / (LON1 - LON0)) * w }
function geoY(lat: number, h: number) { return ((LAT1 - lat) / (LAT1 - LAT0)) * h }
function geo(lon: number, lat: number, w: number, h: number): [number, number] {
  return [geoX(lon, w), geoY(lat, h)]
}

// ── Types ──────────────────────────────────────────────────────────────────────
type IFF    = 'FRIENDLY' | 'HOSTILE' | 'UNKNOWN'
type Domain = 'surface' | 'subsurface' | 'air' | 'mine'

interface Track {
  tn: string; callsign: string; hull?: string
  iff: IFF; domain: Domain
  lon: number; lat: number; vlon: number; vlat: number
  heading: number; speed: number; altitude?: number
  link16: boolean; quality: number
  engaged?: string; mission: string; weapons?: string
}

// ── Colors ─────────────────────────────────────────────────────────────────────
const C = {
  friend:  '#34d399',
  hostile: '#ef4444',
  unknown: '#facc15',
  link16:  '#22d3ee',
}
function iffColor(iff: IFF) {
  return iff === 'FRIENDLY' ? C.friend : iff === 'HOSTILE' ? C.hostile : C.unknown
}

// ── Track database ─────────────────────────────────────────────────────────────
function initTracks(): Track[] {
  return [
    /* FRIENDLY SURFACE */
    { tn:'TN-1042', callsign:'SAG BRAVO',     hull:'DDG-107/CG-73',    iff:'FRIENDLY', domain:'surface',    lon:55.70, lat:25.85, vlon: 0.0010, vlat: 0.0004, heading: 75, speed:12, link16:true,  quality:6, mission:'AAW PICKET / ASCM GUARD',    weapons:'SM-6×24 | SM-2×32 | TLAM×16' },
    { tn:'TN-1044', callsign:'USS TR COLE',   hull:'DDG-80',           iff:'FRIENDLY', domain:'surface',    lon:57.90, lat:24.93, vlon:-0.0005, vlat: 0.0003, heading:210, speed:12, link16:true,  quality:9, mission:'AAW SCREEN — GOM PATROL',      weapons:'SM-2×28 SM-6×8' },
    { tn:'TN-1051', callsign:'USS CHIEF',     hull:'MCM-14',           iff:'FRIENDLY', domain:'surface',    lon:56.35, lat:26.48, vlon: 0.0003, vlat: 0.0001, heading: 92, speed: 4, link16:true,  quality:6, mission:'MCM ZB-ALPHA LEAD' },
    { tn:'TN-1052', callsign:'USS GLADIATOR', hull:'MCM-11',           iff:'FRIENDLY', domain:'surface',    lon:56.55, lat:26.42, vlon: 0.0004, vlat:-0.0001, heading:100, speed: 4, link16:true,  quality:6, mission:'MCM ZB-ALPHA TRAIL' },
    { tn:'TN-1060', callsign:'LUSV-α',                                 iff:'FRIENDLY', domain:'surface',    lon:56.05, lat:26.62, vlon: 0.0015, vlat:-0.0006, heading:345, speed:18, link16:true,  quality:5, mission:'ISR + SWARM ATTRITION',       engaged:'TN-4011' },
    { tn:'TN-1061', callsign:'LUSV-β',                                 iff:'FRIENDLY', domain:'surface',    lon:56.25, lat:26.32, vlon: 0.0012, vlat: 0.0007, heading: 55, speed:16, link16:true,  quality:5, mission:'MINE DETECT / ISR' },
    { tn:'TN-1062', callsign:'LUSV-γ',                                 iff:'FRIENDLY', domain:'surface',    lon:57.10, lat:26.12, vlon:-0.0010, vlat: 0.0008, heading:145, speed:14, link16:true,  quality:5, mission:'SIGINT RELAY / GOLF-7 TRAIL' },
    /* FRIENDLY SUBSURFACE */
    { tn:'TN-2001', callsign:'SSN-774 VIRGINIA',   hull:'SSN-774',     iff:'FRIENDLY', domain:'subsurface', lon:55.15, lat:26.18, vlon: 0.0006, vlat: 0.0003, heading: 68, speed:10, link16:false, quality:6, mission:'TLAM STRIKE / W CHOKEPOINT',  weapons:'TLAM×12 | MK-48×6' },
    { tn:'TN-2002', callsign:'SSN-777 N.CAROLINA', hull:'SSN-777',     iff:'FRIENDLY', domain:'subsurface', lon:58.10, lat:25.58, vlon:-0.0007, vlat:-0.0002, heading:200, speed: 8, link16:false, quality:6, mission:'SSGN ESCORT / GOLF-8 TRAIL' },
    /* FRIENDLY AIR */
    { tn:'TN-3001', callsign:'HAVOC-11',   hull:'F/A-18F',             iff:'FRIENDLY', domain:'air',        lon:56.80, lat:25.50, vlon: 0.0045, vlat:-0.0022, heading:290, speed:380, altitude:25000, link16:true, quality:6, mission:'CAP / CAS ON CALL' },
    { tn:'TN-3002', callsign:'SENTRY-1',   hull:'E-2D HAWKEYE',        iff:'FRIENDLY', domain:'air',        lon:57.40, lat:24.85, vlon: 0.0022, vlat: 0.0012, heading:178, speed:240, altitude:24000, link16:true, quality:6, mission:'AEW&C — JICO NCS NODE' },
    { tn:'TN-3003', callsign:'POSEIDON-7', hull:'P-8A',                iff:'FRIENDLY', domain:'air',        lon:56.30, lat:25.22, vlon: 0.0030, vlat: 0.0015, heading:110, speed:280, altitude:5000,  link16:true, quality:6, mission:'ASW / CONTACT PROSECUTION' },
    /* HOSTILE SURFACE */
    { tn:'TN-4001', callsign:'GOLF-7',       hull:'IRGCN MINE-LAYER',  iff:'HOSTILE',  domain:'surface',    lon:56.75, lat:26.12, vlon:-0.0008, vlat: 0.0004, heading:240, speed: 4, link16:false, quality:4, mission:'EM-52 RE-SEEDING — ZB-ALPHA THREAT' },
    { tn:'TN-4002', callsign:'GOLF-8',       hull:'IRGCN MINE-LAYER',  iff:'HOSTILE',  domain:'surface',    lon:58.45, lat:25.75, vlon:-0.0004, vlat: 0.0002, heading:195, speed: 3, link16:false, quality:3, mission:'MINE-LAYER — EASTERN CHANNEL' },
    { tn:'TN-4011', callsign:'FAC-SWARM-1',  hull:'THONDOR ×3',        iff:'HOSTILE',  domain:'surface',    lon:56.95, lat:26.82, vlon:-0.0018, vlat: 0.0014, heading:218, speed:28, link16:false, quality:5, mission:'FAST ATTACK — C-802 ARMED' },
    { tn:'TN-4012', callsign:'FAC-SWARM-2',  hull:'THONDOR ×3',        iff:'HOSTILE',  domain:'surface',    lon:56.72, lat:27.00, vlon:-0.0014, vlat: 0.0016, heading:225, speed:24, link16:false, quality:5, mission:'FAST ATTACK SWARM' },
    /* HOSTILE SUBSURFACE */
    { tn:'TN-5001', callsign:'GHADIR-UNK',   hull:'GHADIR-CLASS',      iff:'UNKNOWN',  domain:'subsurface', lon:56.85, lat:26.48, vlon:-0.0005, vlat:-0.0003, heading:162, speed: 5, link16:false, quality:2, mission:'CONTACT — NOT LOCALIZED' },
    /* MINES */
    { tn:'TN-6001', callsign:'EM-52',  iff:'HOSTILE', domain:'mine', lon:56.30, lat:26.56, vlon:0, vlat:0, heading:0, speed:0, link16:false, quality:6, mission:'CONFIRMED INFLUENCE MINE' },
    { tn:'TN-6002', callsign:'EM-52',  iff:'HOSTILE', domain:'mine', lon:56.48, lat:26.62, vlon:0, vlat:0, heading:0, speed:0, link16:false, quality:6, mission:'CONFIRMED INFLUENCE MINE' },
    { tn:'TN-6003', callsign:'EM-52',  iff:'HOSTILE', domain:'mine', lon:56.62, lat:26.72, vlon:0, vlat:0, heading:0, speed:0, link16:false, quality:5, mission:'INFLUENCE MINE — UNVERIFIED' },
    { tn:'TN-6004', callsign:'M-08',   iff:'HOSTILE', domain:'mine', lon:57.18, lat:26.43, vlon:0, vlat:0, heading:0, speed:0, link16:false, quality:3, mission:'MOORED MINE — TENTATIVE' },
  ]
}

// ── Coastline polygons (approximate Hormuz geography) ─────────────────────────
const IRAN_COAST: [number, number][] = [
  [54.5,28.2],[54.5,27.15],[54.8,27.05],[55.2,26.82],[55.45,26.95],[55.65,26.92],
  [55.9,26.92],[56.1,26.90],[56.28,27.18],[56.50,27.08],[56.72,27.05],[56.95,26.88],
  [57.20,26.65],[57.45,26.50],[57.65,26.32],[57.90,26.10],[58.20,25.78],[58.55,25.62],
  [58.85,25.60],[59.0,25.55],[59.0,28.2],
]
const OMAN_COAST: [number, number][] = [
  [54.5,24.8],[54.5,25.38],[54.75,25.45],[55.0,25.30],[55.25,25.18],[55.5,25.08],
  [55.72,25.20],[55.9,25.55],[56.0,25.82],[56.15,26.08],[56.25,26.18],
  [56.40,26.05],[56.55,25.72],[56.75,25.52],[57.0,25.28],[57.25,25.38],
  [57.55,25.52],[57.80,25.55],[58.05,25.38],[58.35,25.18],[58.65,25.02],
  [58.88,25.12],[59.0,25.28],[59.0,24.8],
]
const QESHM: [number, number][] = [
  [55.55,26.65],[55.68,26.82],[55.88,26.90],[56.10,26.88],[56.32,26.83],[56.52,26.75],
  [56.48,26.60],[56.28,26.54],[56.08,26.50],[55.88,26.55],[55.68,26.58],[55.55,26.65],
]
const HORMUZ_I: [number, number][] = [
  [56.42,27.08],[56.48,27.12],[56.56,27.10],[56.52,27.05],[56.42,27.08],
]

// ── Point-in-polygon (ray casting) — water constraint ─────────────────────────
function pointInPolygon(lon: number, lat: number, poly: [number, number][]): boolean {
  let inside = false
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const xi = poly[i][0], yi = poly[i][1], xj = poly[j][0], yj = poly[j][1]
    if (((yi > lat) !== (yj > lat)) && (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi))
      inside = !inside
  }
  return inside
}
function isOnLand(lon: number, lat: number): boolean {
  return pointInPolygon(lon, lat, IRAN_COAST) || pointInPolygon(lon, lat, OMAN_COAST) ||
         pointInPolygon(lon, lat, QESHM)      || pointInPolygon(lon, lat, HORMUZ_I)
}

// ── Predefined water patrol waypoints (surface / subsurface) ─────────────────
// All points verified to lie in Strait or Gulf of Oman open water
const PATROL_ROUTES: Record<string, [number, number][]> = {
  // FRIENDLY SURFACE
  'TN-1042': [[55.70,25.90],[56.00,26.22],[56.42,26.28],[56.00,25.95]],         // SAG BRAVO — W approach / transit lane
  'TN-1044': [[57.80,25.22],[58.10,25.42],[58.50,25.48],[58.20,25.22]],         // USS TR COLE DDG-80 — Gulf of Oman patrol
  'TN-1051': [[56.30,26.35],[56.55,26.38],[56.78,26.22],[56.50,26.20]],         // USS CHIEF — MCM ZB-Alpha
  'TN-1052': [[56.50,26.38],[56.75,26.28],[56.52,26.18],[56.28,26.30]],         // USS GLADIATOR — MCM trail
  'TN-1060': [[56.05,26.35],[56.40,26.42],[56.70,26.20],[56.30,26.10]],         // LUSV-α
  'TN-1061': [[56.20,26.22],[56.55,26.36],[56.80,26.15],[56.40,26.05]],         // LUSV-β
  'TN-1062': [[57.10,25.95],[57.50,25.78],[57.80,25.65],[57.40,25.88]],         // LUSV-γ
  // FRIENDLY SUBSURFACE
  'TN-2001': [[55.20,26.05],[55.60,26.15],[56.05,26.00],[55.60,25.80]],         // SSN-774 — W chokepoint
  'TN-2002': [[58.10,25.55],[58.45,25.40],[58.68,25.28],[58.35,25.32]],         // SSN-777 — Gulf of Oman deep
  // HOSTILE SURFACE
  'TN-4001': [[56.75,26.08],[56.45,26.30],[56.15,26.38],[56.50,26.12]],         // GOLF-7 mine-layer
  'TN-4002': [[58.45,25.68],[58.65,25.45],[58.30,25.28],[58.10,25.52]],         // GOLF-8 mine-layer E
  'TN-4011': [[56.95,26.58],[56.55,26.28],[56.20,26.20],[56.60,26.48]],         // FAC-SWARM-1 attack vectors
  'TN-4012': [[56.72,26.68],[56.38,26.45],[56.10,26.28],[56.50,26.55]],         // FAC-SWARM-2 attack vectors
  // HOSTILE SUBSURFACE
  'TN-5001': [[56.85,26.30],[57.15,26.18],[56.90,25.90],[56.55,26.08]],         // GHADIR — strait lurk
}

// ── Aircraft orbit parameters (racetrack / AEW circle / ASW ladder) ──────────
interface AirOrbit { cLon: number; cLat: number; rLon: number; rLat: number; speed: number; altBase: number; altVar: number }
const AIR_ORBITS: Record<string, AirOrbit> = {
  'TN-3001': { cLon:56.70, cLat:25.78, rLon:0.26, rLat:0.10, speed:0.014, altBase:25000, altVar:2200 }, // HAVOC-11 CAP racetrack
  'TN-3002': { cLon:57.42, cLat:25.62, rLon:0.52, rLat:0.20, speed:0.006, altBase:24000, altVar:400  }, // SENTRY-1 AEW orbit
  'TN-3003': { cLon:56.95, cLat:25.58, rLon:0.58, rLat:0.14, speed:0.009, altBase:5000,  altVar:1200 }, // POSEIDON-7 ASW ladder
}

// ── Per-track mutable simulation state ───────────────────────────────────────
interface SimState { wpIdx: number; orbitAngle: number }
function initSimStates(tracks: Track[]): Map<string, SimState> {
  const m = new Map<string, SimState>()
  tracks.forEach((t, i) => m.set(t.tn, { wpIdx: 0, orbitAngle: (i * 0.72) % (Math.PI * 2) }))
  return m
}

// ── Terrain ────────────────────────────────────────────────────────────────────
function drawTerrain(ctx: CanvasRenderingContext2D, w: number, h: number) {
  const ocean = ctx.createLinearGradient(0, 0, w, h)
  ocean.addColorStop(0, '#020d18'); ocean.addColorStop(0.5, '#031c2d'); ocean.addColorStop(1, '#020e1c')
  ctx.fillStyle = ocean; ctx.fillRect(0, 0, w, h)
  const shallow = ctx.createRadialGradient(w*0.44, h*0.52, 16, w*0.44, h*0.52, h*0.32)
  shallow.addColorStop(0, 'rgba(6,66,115,0.22)'); shallow.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = shallow; ctx.fillRect(0, 0, w, h)

  function fillLand(pts: [number, number][], fill: string) {
    ctx.beginPath()
    const [x0, y0] = geo(pts[0][0], pts[0][1], w, h); ctx.moveTo(x0, y0)
    for (let i = 1; i < pts.length; i++) { const [xi, yi] = geo(pts[i][0], pts[i][1], w, h); ctx.lineTo(xi, yi) }
    ctx.closePath(); ctx.fillStyle = fill; ctx.fill()
    ctx.strokeStyle = 'rgba(52,211,153,0.18)'; ctx.lineWidth = 1; ctx.stroke()
  }
  fillLand(IRAN_COAST, '#172417'); fillLand(OMAN_COAST, '#14211a')
  fillLand(QESHM, '#1a2a1a');      fillLand(HORMUZ_I, '#162216')

  // Mountain contour hints
  ctx.save()
  for (let e = 1; e <= 3; e++) {
    const t = e / 4.5
    ctx.beginPath()
    ctx.moveTo(0, geoY(LAT1 - t*0.5, h))
    ctx.bezierCurveTo(w*0.25, geoY(LAT1 - t*0.6, h), w*0.55, geoY(LAT1 - t*0.55, h), w, geoY(LAT1 - t*0.5, h))
    ctx.strokeStyle = `rgba(34,211,153,${0.025 + t*0.02})`; ctx.lineWidth = 1
    ctx.setLineDash([10, 14]); ctx.stroke(); ctx.setLineDash([])
  }
  ctx.restore()

  ctx.font = '8px "JetBrains Mono",monospace'; ctx.fillStyle = 'rgba(161,161,170,0.28)'
  const GEO_LABELS: [string, number, number][] = [
    ['IRAN',56.50,27.70],['BANDAR ABBAS',56.15,27.22],['QESHM IS.',56.00,26.72],
    ['HORMUZ IS.',56.58,27.03],['UAE / OMAN',55.80,25.06],['MUSANDAM (OMAN)',55.90,25.98],
    ['GULF OF OMAN',57.80,25.08],['PERSIAN GULF',55.10,26.55],
  ]
  for (const [txt, lon, lat] of GEO_LABELS) { const [lx, ly] = geo(lon, lat, w, h); ctx.fillText(txt, lx, ly) }
}

// ── Lat/Lon grid ───────────────────────────────────────────────────────────────
function drawGrid(ctx: CanvasRenderingContext2D, w: number, h: number) {
  ctx.save()
  ctx.strokeStyle = 'rgba(16,185,129,0.055)'; ctx.lineWidth = 1
  ctx.font = '7px "JetBrains Mono",monospace'; ctx.fillStyle = 'rgba(16,185,129,0.30)'
  for (let lon = Math.ceil(LON0*2)/2; lon <= LON1; lon += 0.5) {
    const x = geoX(lon, w)
    ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,h); ctx.stroke()
    ctx.fillText(`${lon.toFixed(1)}E`, x+2, h-4)
  }
  for (let lat = Math.ceil(LAT0*2)/2; lat <= LAT1; lat += 0.5) {
    const y = geoY(lat, h)
    ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(w,y); ctx.stroke()
    ctx.fillText(`${lat.toFixed(1)}N`, 2, y-2)
  }
  ctx.restore()
}

// ── Tactical overlays (MCM, danger zone, shipping lane) ────────────────────────
function drawOverlays(ctx: CanvasRenderingContext2D, w: number, h: number) {
  // MCM ZB-Alpha lane
  ctx.save()
  ctx.beginPath()
  const [n0x,n0y]=geo(56.15,26.76,w,h), [n1x,n1y]=geo(56.90,26.74,w,h)
  const [s0x,s0y]=geo(56.15,26.64,w,h), [s1x,s1y]=geo(56.90,26.62,w,h)
  ctx.moveTo(n0x,n0y); ctx.lineTo(n1x,n1y); ctx.lineTo(s1x,s1y); ctx.lineTo(s0x,s0y); ctx.closePath()
  ctx.fillStyle = 'rgba(34,211,238,0.07)'; ctx.fill()
  ctx.strokeStyle = 'rgba(34,211,238,0.45)'; ctx.lineWidth=1; ctx.setLineDash([5,4]); ctx.stroke(); ctx.setLineDash([])
  ctx.fillStyle='rgba(34,211,238,0.60)'; ctx.font='bold 7px "JetBrains Mono",monospace'
  const [mi,miy]=geo(56.38,26.715,w,h); ctx.fillText('ZB-α MCM LANE  67% CLEARED', mi, miy)
  ctx.restore()

  // Danger zone
  ctx.save()
  const [dz0x,dz0y]=geo(57.05,26.85,w,h),[dz1x,dz1y]=geo(58.55,26.85,w,h)
  const [dz2x,dz2y]=geo(58.55,26.22,w,h),[dz3x,dz3y]=geo(57.05,26.22,w,h)
  ctx.beginPath(); ctx.moveTo(dz0x,dz0y); ctx.lineTo(dz1x,dz1y); ctx.lineTo(dz2x,dz2y); ctx.lineTo(dz3x,dz3y); ctx.closePath()
  ctx.fillStyle='rgba(127,29,29,0.08)'; ctx.fill()
  ctx.strokeStyle='rgba(239,68,68,0.22)'; ctx.lineWidth=1; ctx.setLineDash([3,5]); ctx.stroke(); ctx.setLineDash([])
  ctx.fillStyle='rgba(239,68,68,0.42)'; ctx.font='bold 7px "JetBrains Mono",monospace'
  const [dc,dcy]=geo(57.80,26.56,w,h); ctx.fillText('⚠ MINE DANGER — UNSWEPT', dc-46, dcy)
  ctx.restore()

  // Suspended shipping lane
  ctx.save()
  ctx.strokeStyle='rgba(251,191,36,0.13)'; ctx.lineWidth=5; ctx.setLineDash([10,12])
  const [sl0x,sl0y]=geo(54.6,26.22,w,h),[sl1x,sl1y]=geo(56.4,26.38,w,h)
  const [sl2x,sl2y]=geo(57.8,26.12,w,h),[sl3x,sl3y]=geo(58.9,25.65,w,h)
  ctx.beginPath(); ctx.moveTo(sl0x,sl0y); ctx.bezierCurveTo(sl1x,sl1y,sl2x,sl2y,sl3x,sl3y)
  ctx.stroke(); ctx.setLineDash([])
  ctx.fillStyle='rgba(251,191,36,0.22)'; ctx.font='7px "JetBrains Mono",monospace'
  const [slm,slmy]=geo(56.8,26.04,w,h); ctx.fillText('SHIPPING LANE  (SUSPENDED — IMO FORCE MAJEURE)', slm-60, slmy)
  ctx.restore()

  // Strait label
  ctx.save()
  ctx.fillStyle='rgba(52,211,153,0.22)'; ctx.font='bold 11px "JetBrains Mono",monospace'
  const [stx,sty]=geo(56.18,26.50,w,h); ctx.fillText('STRAIT OF HORMUZ', stx, sty)
  ctx.restore()

  // Compass
  ctx.save()
  ctx.fillStyle='rgba(16,185,129,0.55)'; ctx.font='bold 9px "JetBrains Mono",monospace'; ctx.fillText('N', w-22, 16)
  ctx.strokeStyle='rgba(16,185,129,0.45)'; ctx.lineWidth=1.5
  ctx.beginPath(); ctx.moveTo(w-18,8); ctx.lineTo(w-18,24); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(w-26,16); ctx.lineTo(w-10,16); ctx.stroke()
  ctx.restore()

  // Scale bar (~20 nm)
  ctx.save()
  const bar20 = (20/60) * (w/(LON1-LON0))
  const sbx=w-110, sby=h-10
  ctx.strokeStyle='rgba(16,185,129,0.40)'; ctx.lineWidth=1.5
  ctx.beginPath(); ctx.moveTo(sbx,sby); ctx.lineTo(sbx+bar20,sby); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(sbx,sby-3); ctx.lineTo(sbx,sby+3); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(sbx+bar20,sby-3); ctx.lineTo(sbx+bar20,sby+3); ctx.stroke()
  ctx.fillStyle='rgba(16,185,129,0.45)'; ctx.font='7px "JetBrains Mono",monospace'
  ctx.fillText('20 NM', sbx+bar20/2-10, sby-3)
  ctx.restore()
}

// ── MIL-STD-2525 NTDS symbol drawing ──────────────────────────────────────────
function drawNTDS(ctx: CanvasRenderingContext2D, t: Track, x: number, y: number, r: number, tick: number) {
  const col = iffColor(t.iff)
  ctx.save(); ctx.shadowColor=col; ctx.shadowBlur=t.iff==='HOSTILE'?12:8
  ctx.strokeStyle=col; ctx.lineWidth=1.5

  if (t.domain === 'mine') {
    const p = (tick%100)/100
    ctx.beginPath(); ctx.arc(x,y,14+p*22,0,Math.PI*2)
    ctx.strokeStyle=`rgba(239,68,68,${0.18*(1-p)})`; ctx.lineWidth=1; ctx.stroke()
    ctx.strokeStyle=col; ctx.lineWidth=1.5
    ctx.beginPath(); ctx.moveTo(x,y-r); ctx.lineTo(x+r,y); ctx.lineTo(x,y+r); ctx.lineTo(x-r,y); ctx.closePath()
    ctx.stroke(); ctx.fillStyle=col+'16'; ctx.fill()
    ctx.lineWidth=1
    ctx.beginPath()
    ctx.moveTo(x-r*0.45,y-r*0.45); ctx.lineTo(x+r*0.45,y+r*0.45)
    ctx.moveTo(x+r*0.45,y-r*0.45); ctx.lineTo(x-r*0.45,y+r*0.45)
    ctx.stroke()

  } else if (t.domain === 'surface') {
    if (t.iff === 'FRIENDLY') {
      ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.stroke()
      ctx.fillStyle=col+'14'; ctx.fill()
      ctx.lineWidth=1; ctx.beginPath(); ctx.moveTo(x-r*0.4,y+r); ctx.lineTo(x+r*0.4,y+r); ctx.stroke()
    } else {
      ctx.beginPath(); ctx.moveTo(x,y-r); ctx.lineTo(x+r,y); ctx.lineTo(x,y+r); ctx.lineTo(x-r,y); ctx.closePath()
      ctx.stroke(); ctx.fillStyle=col+'18'; ctx.fill()
      if (t.callsign.startsWith('FAC')) {
        const pp=(tick%55)/55
        ctx.beginPath(); ctx.arc(x,y,r+7+pp*11,0,Math.PI*2)
        ctx.strokeStyle=`rgba(239,68,68,${0.35*(1-pp)})`; ctx.lineWidth=1; ctx.stroke()
      }
    }

  } else if (t.domain === 'subsurface') {
    if (t.iff === 'FRIENDLY') {
      ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI); ctx.closePath(); ctx.stroke()
      ctx.fillStyle=col+'12'; ctx.fill()
      ctx.lineWidth=1; ctx.setLineDash([2,3])
      ctx.beginPath(); ctx.moveTo(x-r,y); ctx.lineTo(x+r,y); ctx.stroke(); ctx.setLineDash([])
    } else {
      ctx.lineWidth=1.5; ctx.beginPath(); ctx.moveTo(x-r,y); ctx.lineTo(x,y+r); ctx.lineTo(x+r,y); ctx.stroke()
      ctx.lineWidth=1; ctx.setLineDash([3,4]); ctx.strokeStyle=col+'66'
      ctx.beginPath(); ctx.moveTo(x-r,y); ctx.lineTo(x,y-r); ctx.lineTo(x+r,y); ctx.stroke(); ctx.setLineDash([])
    }

  } else if (t.domain === 'air') {
    if (t.iff === 'FRIENDLY') {
      ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.stroke(); ctx.fillStyle=col+'10'; ctx.fill()
      ctx.lineWidth=1.5
      ctx.beginPath(); ctx.moveTo(x,y-r*0.55); ctx.lineTo(x+r*0.42,y+r*0.35); ctx.lineTo(x-r*0.42,y+r*0.35); ctx.closePath(); ctx.stroke()
    } else {
      ctx.beginPath(); ctx.moveTo(x,y-r); ctx.lineTo(x+r,y); ctx.lineTo(x,y+r); ctx.lineTo(x-r,y); ctx.closePath()
      ctx.stroke(); ctx.fillStyle=col+'18'; ctx.fill()
      ctx.lineWidth=1; ctx.beginPath()
      ctx.moveTo(x-r*0.38,y-r*0.28); ctx.lineTo(x,y+r*0.32); ctx.lineTo(x+r*0.38,y-r*0.28); ctx.stroke()
    }
  }
  ctx.restore()
}

// ── Heading leader ─────────────────────────────────────────────────────────────
function drawHeadingLeader(ctx: CanvasRenderingContext2D, t: Track, x: number, y: number) {
  if (t.speed === 0) return
  const col = iffColor(t.iff)
  const ang = (t.heading - 90) * (Math.PI / 180)
  const len = Math.max(14, Math.min(42, t.speed * 0.62))
  ctx.save(); ctx.strokeStyle=col+'88'; ctx.lineWidth=1; ctx.setLineDash([3,4])
  ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(x+Math.cos(ang)*len, y+Math.sin(ang)*len)
  ctx.stroke(); ctx.setLineDash([]); ctx.restore()
}

// ── NTDS track label (TN / callsign / V C / altitude / L16) ───────────────────
function drawLabel(ctx: CanvasRenderingContext2D, t: Track, x: number, y: number, r: number) {
  const col = iffColor(t.iff); const ox=r+5, oy=-4
  ctx.save(); ctx.shadowBlur=0
  ctx.fillStyle=col; ctx.font='bold 7px "JetBrains Mono",monospace'; ctx.fillText(t.tn, x+ox, y+oy)
  ctx.font='7px "JetBrains Mono",monospace'; ctx.fillStyle=col+'cc'; ctx.fillText(t.callsign, x+ox, y+oy+8)
  if (t.speed>0) {
    ctx.fillStyle=col+'85'; ctx.fillText(`V${Math.round(t.speed)} C${String(Math.round(t.heading)).padStart(3,'0')}`, x+ox, y+oy+16)
  }
  if (t.altitude!=null) { ctx.fillStyle=col+'70'; ctx.fillText(`${Math.round(t.altitude/1000)}K`, x+ox, y+oy+24) }
  if (t.link16) { ctx.fillStyle=C.link16+'aa'; ctx.fillText('L16', x+ox, y+oy+(t.altitude!=null?32:t.speed>0?24:16)) }
  ctx.restore()
}

// ── Wake trail ─────────────────────────────────────────────────────────────────
function drawWake(ctx: CanvasRenderingContext2D, history: [number,number][], iff: IFF) {
  if (history.length < 2) return
  const rgb = iff==='FRIENDLY'?'52,211,153':iff==='HOSTILE'?'239,68,68':'250,204,21'
  ctx.save()
  for (let i=1; i<history.length; i++) {
    ctx.strokeStyle=`rgba(${rgb},${((i/history.length)*0.40).toFixed(2)})`
    ctx.lineWidth=1; ctx.beginPath()
    ctx.moveTo(history[i-1][0],history[i-1][1]); ctx.lineTo(history[i][0],history[i][1]); ctx.stroke()
  }
  ctx.restore()
}

// ── SPY-6 radar sweep (SAG BRAVO) ─────────────────────────────────────────────
function drawRadarSweep(ctx: CanvasRenderingContext2D, tracks: Track[], w: number, h: number, tick: number) {
  const sag = tracks.find(t => t.tn==='TN-1042'); if (!sag) return
  const [sx,sy] = geo(sag.lon, sag.lat, w, h)
  const sa = ((tick*1.8)%360)*Math.PI/180, R=88
  ctx.save()
  ctx.beginPath(); ctx.moveTo(sx,sy); ctx.arc(sx,sy,R,sa-0.28,sa); ctx.closePath()
  const sg = ctx.createRadialGradient(sx,sy,0,sx,sy,R)
  sg.addColorStop(0,'rgba(16,185,129,0.22)'); sg.addColorStop(1,'rgba(16,185,129,0.01)')
  ctx.fillStyle=sg; ctx.fill()
  ctx.strokeStyle='rgba(16,185,129,0.55)'; ctx.lineWidth=1.5
  ctx.beginPath(); ctx.moveTo(sx,sy); ctx.lineTo(sx+Math.cos(sa)*R, sy+Math.sin(sa)*R); ctx.stroke()
  for (const rr of [R*0.5,R]) { ctx.beginPath(); ctx.arc(sx,sy,rr,0,Math.PI*2); ctx.strokeStyle='rgba(16,185,129,0.07)'; ctx.lineWidth=1; ctx.stroke() }
  ctx.fillStyle='rgba(16,185,129,0.35)'; ctx.font='6px "JetBrains Mono",monospace'
  ctx.fillText('SPY-6', sx+6, sy-R*0.95)
  ctx.restore()
}

// ── E-2D AEW sweep ─────────────────────────────────────────────────────────────
function drawE2DRadar(ctx: CanvasRenderingContext2D, tracks: Track[], w: number, h: number, tick: number) {
  const e2d = tracks.find(t => t.tn==='TN-3002'); if (!e2d) return
  const [ex,ey] = geo(e2d.lon, e2d.lat, w, h)
  const ang = ((tick*0.7)%360)*Math.PI/180, R=138
  ctx.save()
  ctx.beginPath(); ctx.moveTo(ex,ey); ctx.arc(ex,ey,R,ang-0.18,ang); ctx.closePath()
  ctx.fillStyle='rgba(34,211,238,0.04)'; ctx.fill()
  ctx.strokeStyle='rgba(34,211,238,0.18)'; ctx.lineWidth=1.5
  ctx.beginPath(); ctx.moveTo(ex,ey); ctx.lineTo(ex+Math.cos(ang)*R, ey+Math.sin(ang)*R); ctx.stroke()
  ctx.beginPath(); ctx.arc(ex,ey,R,0,Math.PI*2)
  ctx.strokeStyle='rgba(34,211,238,0.06)'; ctx.lineWidth=1; ctx.stroke()
  ctx.fillStyle='rgba(34,211,238,0.32)'; ctx.font='6px "JetBrains Mono",monospace'
  ctx.fillText('E-2D AEW', ex+6, ey-R*0.92)
  ctx.restore()
}

// ── Link-16 hub-spoke from E-2D NCS + wolfpack mesh ───────────────────────────
function drawLink16(ctx: CanvasRenderingContext2D, tracks: Track[], w: number, h: number, tick: number) {
  const hub = tracks.find(t => t.tn==='TN-3002'); if (!hub) return
  const [hx,hy] = geo(hub.lon, hub.lat, w, h)
  const nodes = tracks.filter(t => t.link16 && t.iff==='FRIENDLY' && t.tn!==hub.tn)
  for (const node of nodes) {
    const [nx,ny] = geo(node.lon, node.lat, w, h)
    const dx=nx-hx, dy=ny-hy
    ctx.save(); ctx.strokeStyle='rgba(34,211,238,0.09)'; ctx.lineWidth=1; ctx.setLineDash([4,6])
    ctx.beginPath(); ctx.moveTo(hx,hy); ctx.lineTo(nx,ny); ctx.stroke(); ctx.setLineDash([]); ctx.restore()
    const phOffset = parseInt(node.tn.replace(/\D/g,''),10)%70
    const phase = ((tick+phOffset)%80)/80
    if (phase<0.92) {
      ctx.save(); ctx.shadowColor=C.link16; ctx.shadowBlur=7; ctx.fillStyle=C.link16
      ctx.beginPath(); ctx.arc(hx+dx*phase, hy+dy*phase, 2.5, 0, Math.PI*2); ctx.fill(); ctx.restore()
    }
  }
  const wolves = tracks.filter(t => t.callsign.startsWith('LUSV'))
  for (let i=0; i<wolves.length; i++) for (let j=i+1; j<wolves.length; j++) {
    const [ax,ay]=geo(wolves[i].lon,wolves[i].lat,w,h), [bx,by]=geo(wolves[j].lon,wolves[j].lat,w,h)
    ctx.save(); ctx.strokeStyle='rgba(52,211,153,0.07)'; ctx.lineWidth=1; ctx.setLineDash([3,8])
    ctx.beginPath(); ctx.moveTo(ax,ay); ctx.lineTo(bx,by); ctx.stroke(); ctx.setLineDash([]); ctx.restore()
  }
}

// ── Engagement lines ───────────────────────────────────────────────────────────
function drawEngagements(ctx: CanvasRenderingContext2D, tracks: Track[], w: number, h: number, tick: number) {
  for (const t of tracks) {
    if (!t.engaged) continue
    const tgt = tracks.find(x => x.tn===t.engaged); if (!tgt) continue
    const [ax,ay]=geo(t.lon,t.lat,w,h), [bx,by]=geo(tgt.lon,tgt.lat,w,h)
    const phase=(tick%40)/40
    ctx.save()
    ctx.strokeStyle=`rgba(52,211,153,${0.30+phase*0.24})`; ctx.lineWidth=1.5; ctx.setLineDash([5,5])
    ctx.beginPath(); ctx.moveTo(ax,ay); ctx.lineTo(bx,by); ctx.stroke(); ctx.setLineDash([])
    ctx.shadowColor=C.friend; ctx.shadowBlur=8; ctx.fillStyle=C.friend
    ctx.beginPath(); ctx.arc(ax+(bx-ax)*phase, ay+(by-ay)*phase, 3, 0, Math.PI*2); ctx.fill()
    ctx.restore()
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
//  MAIN CANVAS COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════
export function DmoCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const tracksRef = useRef<Track[]>(initTracks())
  const simRef    = useRef<Map<string, SimState>>(initSimStates(tracksRef.current))
  const wakesRef  = useRef<Map<string, [number,number][]>>(new Map())
  const animRef   = useRef<number | null>(null)
  const tickRef   = useRef(0)
  const [running, setRunning]       = useState(true)
  const [selectedTN, setSelectedTN] = useState<string | null>(null)

  const drawFrame = useCallback(() => {
    const canvas = canvasRef.current; if (!canvas) return
    const ctx = canvas.getContext('2d'); if (!ctx) return
    const w = canvas.width, h = canvas.height
    const tick = tickRef.current++

    // ── Advance track positions — water-constrained simulation ───────────────
    tracksRef.current = tracksRef.current.map(t => {
      if (t.speed === 0) return t          // mines stationary
      const st = simRef.current.get(t.tn)
      if (!st) return t

      // ── Aircraft: elliptical racetrack / AEW orbit ────────────────────────
      if (t.domain === 'air') {
        const orb = AIR_ORBITS[t.tn]
        if (!orb) return t
        st.orbitAngle += orb.speed
        const newLon = orb.cLon + orb.rLon * Math.cos(st.orbitAngle)
        const newLat = orb.cLat + orb.rLat * Math.sin(st.orbitAngle)
        // Heading = ellipse tangent direction
        const tLon = -orb.rLon * Math.sin(st.orbitAngle)
        const tLat =  orb.rLat * Math.cos(st.orbitAngle)
        const heading = ((Math.atan2(tLon, tLat) * 180 / Math.PI) + 360) % 360
        const alt = orb.altBase + orb.altVar * Math.sin(st.orbitAngle * 3.3)
        return { ...t, lon: newLon, lat: newLat, heading: Math.round(heading), altitude: Math.round(Math.abs(alt)) }
      }

      // ── Surface / subsurface: waypoint navigation ─────────────────────────
      const route = PATROL_ROUTES[t.tn]
      if (!route) return t
      const [wLon, wLat] = route[st.wpIdx % route.length]
      const dLon = wLon - t.lon, dLat = wLat - t.lat
      const dist  = Math.sqrt(dLon * dLon + dLat * dLat)
      // Advance to next waypoint when close enough
      if (dist < 0.035) {
        st.wpIdx = (st.wpIdx + 1) % route.length
        return t
      }
      // Step proportional to track speed (knots → deg/tick, empirical visual scale)
      const step  = t.speed * 0.000058
      const nLon  = t.lon + (dLon / dist) * step
      const nLat  = t.lat + (dLat / dist) * step
      // Water safety — if step lands on land, skip and jump to next waypoint
      if (isOnLand(nLon, nLat)) {
        st.wpIdx = (st.wpIdx + 1) % route.length
        return t
      }
      const heading = ((Math.atan2(dLon, dLat) * 180 / Math.PI) + 360) % 360
      return { ...t, lon: nLon, lat: nLat, heading: Math.round(heading) }
    })

    // Update wake ring-buffers
    if (tick%4===0) {
      for (const t of tracksRef.current) {
        if (t.speed===0) continue
        const [px,py]=geo(t.lon,t.lat,w,h)
        const hist = wakesRef.current.get(t.tn) ?? []
        hist.push([px,py]); if (hist.length>28) hist.shift()
        wakesRef.current.set(t.tn, hist)
      }
    }

    // Render pipeline
    drawTerrain(ctx, w, h)
    drawGrid(ctx, w, h)
    drawOverlays(ctx, w, h)
    drawE2DRadar(ctx, tracksRef.current, w, h, tick)
    drawLink16(ctx, tracksRef.current, w, h, tick)
    drawRadarSweep(ctx, tracksRef.current, w, h, tick)
    drawEngagements(ctx, tracksRef.current, w, h, tick)

    // Wake trails
    for (const t of tracksRef.current) {
      const hist = wakesRef.current.get(t.tn)
      if (hist) drawWake(ctx, hist, t.iff)
    }

    // NTDS symbols
    const R=7
    for (const t of tracksRef.current) {
      const [x,y]=geo(t.lon,t.lat,w,h)
      drawNTDS(ctx, t, x, y, R, tick)
      drawHeadingLeader(ctx, t, x, y)
      drawLabel(ctx, t, x, y, R)
    }

    // Selected track highlight ring
    if (selectedTN) {
      const sel = tracksRef.current.find(t=>t.tn===selectedTN)
      if (sel) {
        const [x,y]=geo(sel.lon,sel.lat,w,h)
        ctx.save(); ctx.strokeStyle='#ffffff'; ctx.lineWidth=1; ctx.setLineDash([3,3])
        ctx.beginPath(); ctx.arc(x,y,15,0,Math.PI*2); ctx.stroke(); ctx.setLineDash([]); ctx.restore()
      }
    }

    // HUD stamps
    ctx.fillStyle='rgba(16,185,129,0.45)'; ctx.font='8px "JetBrains Mono",monospace'
    const utc = new Date().toLocaleTimeString('en-US',{hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit',timeZone:'UTC'})
    ctx.fillText(`${toDTG(getConflictDay())}  UTC ${utc}  DAY ${getConflictDay()}  NTDS/AEGIS TRACK PICTURE`, 8, 13)
    ctx.fillStyle='rgba(34,211,238,0.38)'; ctx.font='7px "JetBrains Mono",monospace'
    ctx.fillText('◈ ATLAS-7 AI FUSED POS  ·  ADS-B CORR + AIS VESSEL REPORT + NEXUS TRIANGULATION  ·  UPDATE CYCLE: 10s', 8, 24)
    ctx.fillStyle='rgba(16,185,129,0.45)'; ctx.font='8px "JetBrains Mono",monospace'
    ctx.fillText('NAVCENT COP — LINK-16 COMPOSITE — JADC2 LIVE  ·  WATER-CONSTRAINED SIM', 8, h-5)
  }, [selectedTN])

  const startLoop = useCallback(() => {
    const loop = () => { drawFrame(); animRef.current = requestAnimationFrame(loop) }
    animRef.current = requestAnimationFrame(loop)
  }, [drawFrame])

  const stopLoop = useCallback(() => {
    if (animRef.current!==null) { cancelAnimationFrame(animRef.current); animRef.current=null }
  }, [])

  useEffect(() => { if (running) startLoop(); else stopLoop(); return stopLoop }, [running, startLoop, stopLoop])

  const handleReset = () => {
    tracksRef.current = initTracks()
    simRef.current    = initSimStates(tracksRef.current)
    wakesRef.current  = new Map()
    tickRef.current   = 0
    if (!running) drawFrame()
  }

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current; if (!canvas) return
    const r = canvas.getBoundingClientRect()
    const mx=(e.clientX-r.left)*(canvas.width/r.width), my=(e.clientY-r.top)*(canvas.height/r.height)
    const w=canvas.width, h=canvas.height
    let nearest: Track|null=null, minD=22
    for (const t of tracksRef.current) {
      const [tx,ty]=geo(t.lon,t.lat,w,h); const d=Math.hypot(mx-tx,my-ty)
      if (d<minD) { minD=d; nearest=t }
    }
    setSelectedTN(nearest?.tn ?? null)
  }, [])

  const selTrack = selectedTN ? tracksRef.current.find(t=>t.tn===selectedTN) : null

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <button onClick={()=>setRunning(v=>!v)} aria-label={running ? 'Pause simulation' : 'Play simulation'} className="flex items-center gap-2 px-4 min-h-[40px] text-xs tracking-widest border border-emerald-800 rounded-lg text-emerald-400 hover:bg-emerald-950/50 active:scale-95 transition-all duration-150">
          {running ? <Pause size={14}/> : <Play size={14}/>}
          {running ? 'PAUSE' : 'PLAY'}
        </button>
        <button onClick={handleReset} aria-label="Reset simulation" className="flex items-center gap-2 px-4 min-h-[40px] text-xs tracking-widest border border-zinc-700 rounded-lg text-zinc-400 hover:border-zinc-500 active:scale-95 transition-all duration-150">
          <RotateCcw size={14}/> RESET
        </button>
        <span className="text-[9px] text-zinc-600 tracking-widest">{running?'● LIVE COMPOSITE':'■ PAUSED'}</span>
        {selectedTN && <span className="ml-auto text-[9px] text-amber-400 tracking-widest">SELECTED: {selectedTN} — click again to deselect</span>}
      </div>

      <div className="border border-emerald-900/50 rounded-sm overflow-hidden" style={{boxShadow:'0 0 24px rgba(16,185,129,0.06)'}}>
        <canvas
          ref={canvasRef} width={880} height={468}
          className="w-full block bg-zinc-950 cursor-crosshair"
          style={{maxHeight:'468px'}}
          onClick={handleClick}
          role="img"
          aria-label="NTDS/AEGIS tactical display — Strait of Hormuz JADC2"
        />
      </div>

      {selTrack && (
        <div className="tac-card p-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-[9px] border-amber-900/60">
          <div>
            <p className="text-zinc-600 tracking-widest">TRACK</p>
            <p className={`font-bold tracking-widest mt-0.5 ${selTrack.iff==='FRIENDLY'?'text-emerald-400':selTrack.iff==='HOSTILE'?'text-red-400':'text-amber-400'}`}>{selTrack.tn}</p>
            <p className="text-zinc-400 mt-0.5">{selTrack.callsign}</p>
            {selTrack.hull && <p className="text-zinc-600">{selTrack.hull}</p>}
          </div>
          <div>
            <p className="text-zinc-600 tracking-widest">POSITION</p>
            <p className="text-zinc-300 mt-0.5">{selTrack.lat.toFixed(2)}°N</p>
            <p className="text-zinc-300">{selTrack.lon.toFixed(2)}°E</p>
          </div>
          <div>
            <p className="text-zinc-600 tracking-widest">KINEMATIC</p>
            <p className="text-zinc-300 mt-0.5">V {selTrack.speed} kts</p>
            <p className="text-zinc-300">C {String(selTrack.heading).padStart(3,'0')}°T</p>
            {selTrack.altitude!=null && <p className="text-zinc-400">{selTrack.altitude.toLocaleString()} ft</p>}
          </div>
          <div>
            <p className="text-zinc-600 tracking-widest">TASKING</p>
            <p className="text-zinc-400 mt-0.5 leading-relaxed">{selTrack.mission}</p>
            {selTrack.weapons && <p className="text-zinc-600 mt-1">{selTrack.weapons}</p>}
          </div>
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
//  JICO PANEL — Link-16 / TADIL-J + JADC2 Kill Chain
// ═══════════════════════════════════════════════════════════════════════════════
interface JicoNode {
  id: string; unit: string; type: string
  link16: boolean; tadilJ: boolean; link11: boolean
  status: 'ACTIVE' | 'DEGRADED' | 'OFFLINE'; participation: number
}
const JICO_NODES: JicoNode[] = [
  { id:'N01', unit:'USS GRAVELY (DDG-107)',   type:'SURFACE',  link16:true,  tadilJ:true,  link11:true,  status:'ACTIVE',   participation:98 },
  { id:'N02', unit:'USS BUNKER HILL (CG-73)', type:'SURFACE',  link16:true,  tadilJ:true,  link11:true,  status:'ACTIVE',   participation:97 },
  { id:'N03', unit:'USS TR COLE (DDG-80)',      type:'SURFACE',  link16:true,  tadilJ:false, link11:true,  status:'ACTIVE',   participation:94 },
  { id:'N04', unit:'USS CHIEF (MCM-14)',       type:'MCM',      link16:true,  tadilJ:false, link11:false, status:'ACTIVE',   participation:95 },
  { id:'N05', unit:'USS GLADIATOR (MCM-11)',   type:'MCM',      link16:true,  tadilJ:false, link11:false, status:'ACTIVE',   participation:94 },
  { id:'N06', unit:'E-2D SENTRY-1 (NCS)',     type:'AEW/NCS',  link16:true,  tadilJ:true,  link11:true,  status:'ACTIVE',   participation:100},
  { id:'N07', unit:'F/A-18F HAVOC-11',        type:'AIR',      link16:true,  tadilJ:false, link11:false, status:'ACTIVE',   participation:99 },
  { id:'N08', unit:'P-8A POSEIDON-7',         type:'ASW',      link16:true,  tadilJ:true,  link11:false, status:'ACTIVE',   participation:97 },
  { id:'N09', unit:'LUSV-α/β/γ WOLFPACK',     type:'USV MESH', link16:true,  tadilJ:false, link11:false, status:'ACTIVE',   participation:92 },
  { id:'N10', unit:'CENTCOM JADC2 GATEWAY',   type:'C2 NODE',  link16:true,  tadilJ:true,  link11:true,  status:'ACTIVE',   participation:100},
  { id:'N11', unit:'NAVCENT COP SERVER',      type:'C2 NODE',  link16:false, tadilJ:true,  link11:true,  status:'ACTIVE',   participation:100},
  { id:'N12', unit:'WGS-6 SPACE CDL RELAY',   type:'SPACE',    link16:false, tadilJ:true,  link11:false, status:'ACTIVE',   participation:98 },
]

interface KillChain {
  id: string; phase: 'FIND'|'FIX'|'TRACK'|'TARGET'|'ENGAGE'|'ASSESS'
  target: string; sensor: string; shooter: string; elapsed: string
  status: 'ACTIVE'|'PENDING'|'COMPLETE'
}
const KILL_CHAINS: KillChain[] = [
  { id:'KC-01', phase:'TRACK',  target:'TN-4001 GOLF-7 (MINE-LAYER)',  sensor:'LUSV-γ / ATLAS-1',  shooter:'SAG BRAVO / P-8A',   elapsed:'04:17', status:'ACTIVE'  },
  { id:'KC-02', phase:'ENGAGE', target:'TN-4011 FAC-SWARM-1',          sensor:'SPY-6 + LUSV-α',    shooter:'LUSV-α (kinetic)',   elapsed:'01:44', status:'ACTIVE'  },
  { id:'KC-03', phase:'FIX',    target:'TN-5001 GHADIR-UNK (SUB)',     sensor:'P-8A / SSN-777',    shooter:'MK-54 TORPEDO',      elapsed:'08:33', status:'PENDING' },
  { id:'KC-04', phase:'TARGET', target:'TN-4002 GOLF-8 (MINE-LAYER)',  sensor:'SSN-777 / IMINT',   shooter:'TLAM / JASSM-ER',    elapsed:'12:01', status:'PENDING' },
]
const PHASE_COL: Record<KillChain['phase'],string> = {
  FIND:'text-zinc-400', FIX:'text-blue-400', TRACK:'text-cyan-400',
  TARGET:'text-amber-400', ENGAGE:'text-red-400', ASSESS:'text-emerald-400',
}
const PHASES = ['FIND','FIX','TRACK','TARGET','ENGAGE','ASSESS'] as const

export function JicoPanel() {
  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
      {/* Link-16 / TADIL-J node table */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header mb-2">
          <Radio size={11} className="text-cyan-500"/>
          <span>JICO — Link-16 / TADIL-J Network Status</span>
          <span className="ml-auto text-[9px] text-cyan-500 tracking-widest normal-case">NET-A · JTIDS · NCS: E-2D</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[9px]">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-600 tracking-widest uppercase text-[7px]">
                <th className="text-left pb-1.5 pr-2 font-normal">Unit</th>
                <th className="text-left pb-1.5 pr-2 font-normal">Type</th>
                <th className="text-center pb-1.5 pr-1 font-normal">L16</th>
                <th className="text-center pb-1.5 pr-1 font-normal">TADIL-J</th>
                <th className="text-center pb-1.5 pr-2 font-normal">L11</th>
                <th className="text-right pb-1.5 font-normal">Part%</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900/50">
              {JICO_NODES.map(n => (
                <tr key={n.id} className={n.status==='DEGRADED'?'bg-amber-950/10':''}>
                  <td className="py-1 pr-2">
                    <span className={n.status==='ACTIVE'?'text-zinc-300':n.status==='DEGRADED'?'text-amber-400':'text-zinc-600'}>{n.unit}</span>
                  </td>
                  <td className="py-1 pr-2 text-zinc-600 tracking-wider">{n.type}</td>
                  <td className="py-1 pr-1 text-center"><span className={n.link16?'text-cyan-400':'text-zinc-700'}>{n.link16?'●':'○'}</span></td>
                  <td className="py-1 pr-1 text-center"><span className={n.tadilJ?'text-cyan-400':'text-zinc-700'}>{n.tadilJ?'●':'○'}</span></td>
                  <td className="py-1 pr-2 text-center"><span className={n.link11?'text-cyan-400':'text-zinc-700'}>{n.link11?'●':'○'}</span></td>
                  <td className={`py-1 text-right tabular-nums font-bold ${n.participation>=95?'text-emerald-400':n.participation>=70?'text-amber-400':'text-red-400'}`}>
                    {n.participation}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex gap-4 text-[8px] text-zinc-600 pt-1 border-t border-zinc-900">
          <span><span className="text-cyan-400">●</span> Participating</span>
          <span><span className="text-zinc-700">○</span> Not in net</span>
          <span className="ml-auto">TIME: 200812Z MAR 2026</span>
        </div>
      </div>

      {/* JADC2 Kill Chain tracker */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header mb-2">
          <Crosshair size={11} className="text-red-500"/>
          <span>JADC2 Kill Chain — F2T2EA Engagements</span>
          <span className="ml-auto text-[9px] text-red-500 tracking-widest normal-case">{KILL_CHAINS.filter(k=>k.status==='ACTIVE').length} ACTIVE</span>
        </div>

        {/* F2T2EA pipeline bar */}
        <div className="flex items-center text-[7px] tracking-widest mb-3">
          {PHASES.map((phase, i) => (
            <div key={phase} className="flex items-center">
              <div className={`px-2 py-1 border text-center ${KILL_CHAINS.some(k=>k.phase===phase&&k.status==='ACTIVE')?`${PHASE_COL[phase]} border-current bg-current/10`:'text-zinc-700 border-zinc-800'}`}>
                {phase}
              </div>
              {i<5 && <div className="text-zinc-700">›</div>}
            </div>
          ))}
        </div>

        <div className="space-y-2">
          {KILL_CHAINS.map(kc => (
            <div key={kc.id} className={`flex gap-3 text-[9px] p-2 rounded-sm border-l-2 ${kc.status==='ACTIVE'?'border-red-700 bg-red-950/10':'border-zinc-800 bg-zinc-900/20'}`}>
              <div className="shrink-0 w-12">
                <p className="text-zinc-600 tracking-wider">{kc.id}</p>
                <p className={`font-bold tracking-widest mt-0.5 ${PHASE_COL[kc.phase]}`}>{kc.phase}</p>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-zinc-300 font-medium truncate">{kc.target}</p>
                <p className="text-zinc-600 mt-0.5">SNS: {kc.sensor}</p>
                <p className="text-zinc-600">SHT: {kc.shooter}</p>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-zinc-600 tabular-nums">{kc.elapsed}</p>
                <p className={`mt-0.5 font-bold tracking-widest text-[8px] ${kc.status==='ACTIVE'?'text-red-400':'text-zinc-500'}`}>{kc.status}</p>
              </div>
            </div>
          ))}
        </div>
        <p className="text-[8px] text-zinc-700 pt-1 border-t border-zinc-900">
          F2T2EA doctrine · JADC2 per CJCS OPORD 26-FURY · Sensor-to-Shooter attribution
        </p>
      </div>
    </div>
  )
}

// Legacy: keep a placeholder type alias so nothing breaks if AssetKind is referenced elsewhere
// eslint-disable-next-line @typescript-eslint/no-unused-vars
type AssetKind = 'submarine' | 'usv' | 'sag' | 'swarm' | 'mine'
