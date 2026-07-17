'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { Play, Pause, RotateCcw, Layers, Radio } from 'lucide-react'
import { getConflictDay, toDTG } from '@/lib/conflict-day'

// ── Types ──────────────────────────────────────────────────────────────────────
type AirType = 'fighter' | 'bomber' | 'tanker' | 'awacs' | 'hostile' | 'uav' | 'helo'
type MarType = 'carrier' | 'ddg' | 'ssn' | 'mcm' | 'ssgn' | 'irgc_fac' | 'irgc_sub' | 'mine' | 'tanker_civ'

interface AirTrack {
  id: string
  kind: AirType
  callsign: string
  x: number; y: number
  vx: number; vy: number
  alt: number   // feet
  speed: number // knots
  iff: 'friend' | 'hostile' | 'neutral'
  mode: string  // ATC squawk / NCTR label
}

interface MarTrack {
  id: string
  kind: MarType
  mmsi?: string
  name: string
  x: number; y: number
  vx: number; vy: number
  hdg: number  // degrees
  sog: number  // knots
  iff: 'friend' | 'hostile' | 'neutral'
}

// ── Geo-reference: map 0-1 → Persian Gulf region ───────────────────────────────
// WGS84 bounding box approximated: lon 48°E–62°E, lat 22°N–30°N
const BBOX = { lonMin: 48, lonMax: 62, latMin: 22, latMax: 30 }

function geoToCanvas(lon: number, lat: number): { x: number; y: number } {
  return {
    x: (lon - BBOX.lonMin) / (BBOX.lonMax - BBOX.lonMin),
    y: 1 - (lat - BBOX.latMin) / (BBOX.latMax - BBOX.latMin),
  }
}

// ── Color/shape lookup ─────────────────────────────────────────────────────────
const AIR_COLOR: Record<AirTrack['iff'], string> = {
  friend:  '#22d3ee', // cyan-400
  hostile: '#f87171', // red-400
  neutral: '#a3a3a3', // zinc-400
}

const MAR_COLOR: Record<MarTrack['iff'], string> = {
  friend:  '#34d399', // emerald-400
  hostile: '#ef4444', // red-500
  neutral: '#fbbf24', // amber-400
}

// ── Geo features: coastline landmark waypoints ────────────────────────────────
// Approximated from CIA World Factbook / AFSOUTH charting
const GEO_FEATURES = {
  // Persian Gulf polygon (simplified clockwise from Hormuz)
  gulfOutline: [
    geoToCanvas(56.4, 24.1),  // Hormuz narrows east
    geoToCanvas(58.0, 23.5),  // Gulf of Oman entry
    geoToCanvas(59.5, 22.4),  // Arabian Sea open
    geoToCanvas(53.5, 22.5),  // Oman coast
    geoToCanvas(51.5, 24.0),  // UAE/Oman border
    geoToCanvas(51.5, 24.5),  // Abu Dhabi area
    geoToCanvas(54.5, 24.5),  // Qatar approach
    geoToCanvas(51.5, 26.0),  // Qatar
    geoToCanvas(50.5, 26.3),  // Bahrain
    geoToCanvas(49.8, 26.5),  // Al Jubail coast
    geoToCanvas(48.6, 27.5),  // Kuwait
    geoToCanvas(48.0, 29.5),  // Shatt al-Arab
    geoToCanvas(48.5, 30.0),  // Basra
    geoToCanvas(49.5, 30.0),  // Iraq south
    geoToCanvas(50.5, 29.8),  // Iran SW coast (Khuzestan)
    geoToCanvas(51.5, 29.5),  // Iran coast
    geoToCanvas(53.0, 28.5),  // Bushehr
    geoToCanvas(54.0, 27.5),  // Bandar Abbas approach
    geoToCanvas(55.0, 27.0),  // Bandar Abbas
    geoToCanvas(56.0, 26.6),  // Hormuz Island
    geoToCanvas(56.4, 26.3),  // Qeshm Island
    geoToCanvas(56.4, 24.1),  // close polygon
  ],

  // Gulf of Oman outline
  goOman: [
    geoToCanvas(56.4, 24.1),
    geoToCanvas(62.0, 22.5),
    geoToCanvas(61.0, 22.0),
    geoToCanvas(58.5, 22.0),
    geoToCanvas(56.4, 24.1),
  ],

  // Key labels: [lon, lat, text]
  labels: [
    [56.2, 26.55, 'HORMUZ STRAIT'],
    [52.5, 26.1,  'PERSIAN GULF'],
    [58.5, 23.0,  'GULF OF OMAN'],
    [50.6, 26.22, 'BAHRAIN'],
    [51.5, 25.3,  'QATAR'],
    [55.3, 25.3,  'UAE'],
    [50.2, 29.4,  'KUWAIT'],
    [53.1, 28.65, 'BUSHEHR'],
    [56.25, 27.18,'BANDAR ABBAS'],
    [48.5, 30.5,  'IRAQ'],
    [54.0, 32.0,  'IRAN'],
    [56.8, 26.5,  'QESHM I.'],
  ] as [number, number, string][],

  // Airbase markers: [lon, lat, label, side]
  airbases: [
    [51.31, 25.27, 'Al Udeid AB (CAOC)', 'us'],
    [54.55, 24.42, 'Al Dhafra AB', 'us'],
    [50.33, 26.27, 'NSA Bahrain / Sheikh Isa', 'us'],
    [29.59, 29.70, 'Prince Sultan AB', 'us'], // Saudi — off map left edge
    [56.89, 27.20, 'Bandar Abbas (IRGCAF)', 'ir'],
    [51.77, 32.52, 'Isfahan AB (IRIAF)', 'ir'],
    [52.35, 29.55, 'Shiraz AB (IRIAF)', 'ir'],
    [60.88, 25.40, 'Chabahar (Shahed)', 'ir'],
  ] as [number, number, string, 'us' | 'ir'][],

  // SAM threat rings: [lon, lat, radius_deg, label]
  samRings: [
    [56.0, 27.5,  0.6, 'Bavar-373 (DEGRADED)'],
    [51.7, 32.5,  0.5, 'Khordad-15'],
    [60.5, 25.5,  0.4, 'Tor-M1'],
    [52.3, 29.5,  0.45, 'Khordad-15'],
  ] as [number, number, number, string][],

  // MCM corridors: arrays of waypoints
  mcmZbAlpha: [
    geoToCanvas(56.1, 26.0),
    geoToCanvas(56.6, 25.5),
    geoToCanvas(57.2, 25.0),
    geoToCanvas(58.0, 24.5),
  ],

  // AIS-style shipping lane (pre-closure)
  shippingLane: [
    geoToCanvas(56.5, 26.2),
    geoToCanvas(57.5, 25.3),
    geoToCanvas(59.0, 24.0),
    geoToCanvas(61.0, 23.0),
  ],
}

// ── Initial air tracks ─────────────────────────────────────────────────────────
function createAirTracks(): AirTrack[] {
  return [
    // Coalition fighters
    { id: 'a01', kind: 'fighter', callsign: 'VIPER-11',  ...geoToCanvas(51.8, 26.2), vx: 0.0008, vy: -0.0003, alt: 25000, speed: 480, iff: 'friend', mode: '4101' },
    { id: 'a02', kind: 'fighter', callsign: 'VIPER-12',  ...geoToCanvas(52.1, 26.0), vx: 0.0009, vy: -0.0004, alt: 24800, speed: 490, iff: 'friend', mode: '4102' },
    { id: 'a03', kind: 'fighter', callsign: 'HORNET-21', ...geoToCanvas(53.0, 24.8), vx: 0.0012, vy: 0.0002,  alt: 22000, speed: 510, iff: 'friend', mode: '4201' },
    { id: 'a04', kind: 'fighter', callsign: 'HORNET-22', ...geoToCanvas(53.3, 24.5), vx: 0.0010, vy: 0.0003,  alt: 21500, speed: 505, iff: 'friend', mode: '4202' },
    { id: 'a05', kind: 'fighter', callsign: 'RAPTOR-31', ...geoToCanvas(55.0, 25.8), vx: -0.0005,vy: 0.0008,  alt: 35000, speed: 550, iff: 'friend', mode: '4301' },
    { id: 'a06', kind: 'fighter', callsign: 'TYPHOON-1', ...geoToCanvas(54.8, 25.3), vx: 0.0007, vy: -0.0006, alt: 28000, speed: 520, iff: 'friend', mode: '4401' },
    { id: 'a07', kind: 'fighter', callsign: 'RAFALE-11', ...geoToCanvas(57.0, 24.2), vx: -0.0006,vy: 0.0004,  alt: 26000, speed: 495, iff: 'friend', mode: '4501' },
    { id: 'a08', kind: 'fighter', callsign: 'RAFALE-12', ...geoToCanvas(57.3, 24.0), vx: -0.0007,vy: 0.0005,  alt: 26200, speed: 500, iff: 'friend', mode: '4502' },
    // Bomber
    { id: 'a09', kind: 'bomber',  callsign: 'SPIRIT-01', ...geoToCanvas(55.5, 27.5), vx: -0.0004,vy: -0.0002, alt: 45000, speed: 400, iff: 'friend', mode: '5001' },
    // Tankers
    { id: 'a10', kind: 'tanker',  callsign: 'TEXACO-1',  ...geoToCanvas(52.0, 27.0), vx: 0.0003, vy: 0.0001,  alt: 28000, speed: 310, iff: 'friend', mode: '6101' },
    { id: 'a11', kind: 'tanker',  callsign: 'TEXACO-2',  ...geoToCanvas(53.5, 27.0), vx: 0.0002, vy: -0.0001, alt: 27000, speed: 305, iff: 'friend', mode: '6102' },
    // AWACS
    { id: 'a12', kind: 'awacs',   callsign: 'SENTRY-11', ...geoToCanvas(51.0, 27.5), vx: 0.0004, vy: -0.0002, alt: 30000, speed: 290, iff: 'friend', mode: '7001' },
    { id: 'a13', kind: 'awacs',   callsign: 'WEDGETL-1', ...geoToCanvas(52.8, 27.8), vx: -0.0003,vy: 0.0001,  alt: 29000, speed: 285, iff: 'friend', mode: '7002' },
    // UAVs
    { id: 'a14', kind: 'uav',     callsign: 'HAWK-01',   ...geoToCanvas(56.5, 26.8), vx: -0.0007,vy: 0.0006,  alt: 50000, speed: 310, iff: 'friend', mode: '8001' },
    { id: 'a15', kind: 'uav',     callsign: 'HAWK-02',   ...geoToCanvas(57.5, 26.5), vx: -0.0008,vy: 0.0007,  alt: 50500, speed: 315, iff: 'friend', mode: '8002' },
    { id: 'a16', kind: 'uav',     callsign: 'MQ9-REAPER',  ...geoToCanvas(55.8, 27.2),vx:0.0002,vy:0.0004, alt: 25000, speed: 230, iff: 'friend', mode: '8003' },
    // Hostile air (IRIAF — degraded sortie)
    { id: 'h01', kind: 'hostile', callsign: 'BANDIT-α',  ...geoToCanvas(57.5, 27.8), vx: -0.0015,vy: 0.0010, alt: 18000, speed: 560, iff: 'hostile', mode: 'IRIAF' },
    { id: 'h02', kind: 'hostile', callsign: 'BANDIT-β',  ...geoToCanvas(58.0, 28.2), vx: -0.0013,vy: 0.0008, alt: 17500, speed: 545, iff: 'hostile', mode: 'IRIAF' },
    // IRGC Shahed loitering
    { id: 'h03', kind: 'uav',     callsign: 'SHAD-01',   ...geoToCanvas(56.9, 26.9), vx: -0.0020,vy: 0.0015, alt: 5000,  speed: 115, iff: 'hostile', mode: 'SHAD' },
    { id: 'h04', kind: 'uav',     callsign: 'SHAD-02',   ...geoToCanvas(57.1, 26.7), vx: -0.0022,vy: 0.0013, alt: 4800,  speed: 110, iff: 'hostile', mode: 'SHAD' },
    { id: 'h05', kind: 'uav',     callsign: 'SHAD-03',   ...geoToCanvas(57.3, 26.5), vx: -0.0019,vy: 0.0014, alt: 5200,  speed: 118, iff: 'hostile', mode: 'SHAD' },
    // Helo
    { id: 'a17', kind: 'helo',    callsign: 'CHARGER-1', ...geoToCanvas(56.2, 26.3), vx: 0.0003, vy: -0.0002, alt: 100,   speed: 130, iff: 'friend', mode: 'ASW' },
  ]
}

// ── Initial maritime tracks ────────────────────────────────────────────────────
function createMarTracks(): MarTrack[] {
  return [
    // US/Coalition surface
    { id: 'm01', kind: 'carrier',   mmsi: '369012001', name: 'CVN-69 IKE',    ...geoToCanvas(59.0, 23.5), vx: -0.0003, vy: 0.0001, hdg: 270, sog: 12, iff: 'friend' },
    { id: 'm02', kind: 'carrier',   mmsi: '369012002', name: 'CVN-71 TR',     ...geoToCanvas(43.5, 14.5), vx: 0.0002,  vy: -0.0001, hdg: 10,  sog: 10, iff: 'friend' },
    { id: 'm03', kind: 'ddg',       mmsi: '369112107', name: 'DDG-107 GRAVELY',...geoToCanvas(57.5, 25.2), vx: -0.0004, vy: 0.0002,  hdg: 255, sog: 15, iff: 'friend' },
    { id: 'm04', kind: 'ddg',       mmsi: '369108000', name: 'DDG-80 TR COLE', ...geoToCanvas(58.5, 24.0), vx: -0.0002, vy: 0.0001,  hdg: 280, sog: 12, iff: 'friend' },
    { id: 'm05', kind: 'ddg',       mmsi: '369108000', name: 'DDG-80 TR',      ...geoToCanvas(58.8, 23.8), vx: -0.0003, vy: 0.0001,  hdg: 265, sog: 12, iff: 'friend' },
    { id: 'm06', kind: 'ssgn',      mmsi: '369072901', name: 'SSGN-729 GA',    ...geoToCanvas(57.8, 24.5), vx: -0.0001, vy: 0.0000,  hdg: 210, sog: 6,  iff: 'friend' },
    { id: 'm07', kind: 'ssn',       mmsi: '369077401', name: 'SSN-774 VA',     ...geoToCanvas(56.0, 25.8), vx: 0.0002,  vy: -0.0001, hdg: 70,  sog: 8,  iff: 'friend' },
    { id: 'm08', kind: 'ssn',       mmsi: '369077700', name: 'SSN-777 NC',     ...geoToCanvas(56.8, 25.5), vx: -0.0002, vy: 0.0001,  hdg: 190, sog: 7,  iff: 'friend' },
    { id: 'm09', kind: 'mcm',       mmsi: '369001401', name: 'MCM-14 CHIEF',   ...geoToCanvas(56.3, 26.1), vx: 0.0005,  vy: -0.0003, hdg: 65,  sog: 4,  iff: 'friend' },
    { id: 'm10', kind: 'mcm',       mmsi: '369001101', name: 'MCM-11 GLAD',    ...geoToCanvas(56.5, 26.0), vx: 0.0004,  vy: -0.0003, hdg: 70,  sog: 4,  iff: 'friend' },
    // British
    { id: 'm11', kind: 'ddg',       mmsi: '234567890', name: 'D34 DIAMOND',    ...geoToCanvas(44.0, 14.8), vx: 0.0002,  vy: -0.0001, hdg: 355, sog: 14, iff: 'friend' },
    // CDG group
    { id: 'm12', kind: 'carrier',   mmsi: '226000001', name: 'R91 CDG',        ...geoToCanvas(60.5, 23.0), vx: -0.0003, vy: 0.0001,  hdg: 280, sog: 11, iff: 'friend' },
    // IRGC
    { id: 'i01', kind: 'irgc_fac',  name: 'IRGCN FAC-1', ...geoToCanvas(56.1, 26.7), vx: -0.0020, vy: 0.0010, hdg: 220, sog: 28, iff: 'hostile' },
    { id: 'i02', kind: 'irgc_fac',  name: 'IRGCN FAC-2', ...geoToCanvas(56.3, 26.8), vx: -0.0018, vy: 0.0012, hdg: 215, sog: 30, iff: 'hostile' },
    { id: 'i03', kind: 'irgc_fac',  name: 'IRGCN FAC-3', ...geoToCanvas(56.5, 26.9), vx: -0.0022, vy: 0.0009, hdg: 225, sog: 27, iff: 'hostile' },
    { id: 'i04', kind: 'irgc_sub',  name: 'GOLF-7 (MINE)',  ...geoToCanvas(56.0, 26.5), vx: -0.0005, vy: 0.0003, hdg: 200, sog: 5, iff: 'hostile' },
    { id: 'i05', kind: 'irgc_sub',  name: 'KILO-1',      ...geoToCanvas(58.2, 24.8), vx: 0.0004, vy: -0.0002, hdg: 135, sog: 6, iff: 'hostile' },
    // Mines
    { id: 'n01', kind: 'mine', name: 'EM-52 #1', ...geoToCanvas(56.2, 26.3), vx: 0, vy: 0, hdg: 0, sog: 0, iff: 'hostile' },
    { id: 'n02', kind: 'mine', name: 'EM-52 #2', ...geoToCanvas(56.4, 26.1), vx: 0, vy: 0, hdg: 0, sog: 0, iff: 'hostile' },
    { id: 'n03', kind: 'mine', name: 'EM-52 #3', ...geoToCanvas(56.6, 26.4), vx: 0, vy: 0, hdg: 0, sog: 0, iff: 'hostile' },
    { id: 'n04', kind: 'mine', name: 'EM-52 #4', ...geoToCanvas(56.8, 26.2), vx: 0, vy: 0, hdg: 0, sog: 0, iff: 'hostile' },
    { id: 'n05', kind: 'mine', name: 'EM-52 #5', ...geoToCanvas(57.0, 26.0), vx: 0, vy: 0, hdg: 0, sog: 0, iff: 'hostile' },
    { id: 'n06', kind: 'mine', name: 'EM-52 #6', ...geoToCanvas(56.9, 26.6), vx: 0, vy: 0, hdg: 0, sog: 0, iff: 'hostile' },
    // AIS civilian (tankers rerouting)
    { id: 'c01', kind: 'tanker_civ', mmsi: '477123456', name: 'MT GULF SPIRIT [AIS]', ...geoToCanvas(60.5, 22.8), vx: 0.0004,  vy: 0.0001,  hdg: 95,  sog: 12, iff: 'neutral' },
    { id: 'c02', kind: 'tanker_civ', mmsi: '477654321', name: 'MT HORIZON [AIS]',      ...geoToCanvas(61.0, 22.5), vx: -0.0002, vy: 0.0001,  hdg: 270, sog: 11, iff: 'neutral' },
  ]
}

// ── Draw engines ───────────────────────────────────────────────────────────────

function drawGeoBackground(ctx: CanvasRenderingContext2D, w: number, h: number) {
  // Deep ocean fill
  const grad = ctx.createLinearGradient(0, 0, w, h)
  grad.addColorStop(0, '#010d14')
  grad.addColorStop(1, '#020f1c')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, w, h)

  // Tactical grid
  ctx.strokeStyle = 'rgba(16,185,129,0.05)'
  ctx.lineWidth = 0.5
  const gs = 50
  for (let gx = 0; gx < w; gx += gs) { ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, h); ctx.stroke() }
  for (let gy = 0; gy < h; gy += gs) { ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(w, gy); ctx.stroke() }

  function toScreen(pt: { x: number; y: number }): [number, number] {
    return [pt.x * w, pt.y * h]
  }

  // Gulf fill (water)
  ctx.beginPath()
  const gulfPts = GEO_FEATURES.gulfOutline
  const [gx0, gy0] = toScreen(gulfPts[0])
  ctx.moveTo(gx0, gy0)
  for (let i = 1; i < gulfPts.length; i++) {
    const [gxi, gyi] = toScreen(gulfPts[i])
    ctx.lineTo(gxi, gyi)
  }
  ctx.closePath()
  ctx.fillStyle = 'rgba(6,66,115,0.35)'
  ctx.fill()
  ctx.strokeStyle = 'rgba(6,182,212,0.25)'
  ctx.lineWidth = 1.5
  ctx.stroke()

  // Gulf of Oman fill
  ctx.beginPath()
  const goOman = GEO_FEATURES.goOman
  const [g2x, g2y] = toScreen(goOman[0])
  ctx.moveTo(g2x, g2y)
  for (let i = 1; i < goOman.length; i++) {
    const [gi, gj] = toScreen(goOman[i])
    ctx.lineTo(gi, gj)
  }
  ctx.closePath()
  ctx.fillStyle = 'rgba(6,66,115,0.25)'
  ctx.fill()

  // Shipping lane (dashed, pre-closure)
  ctx.strokeStyle = 'rgba(251,191,36,0.15)'
  ctx.lineWidth = 6
  ctx.setLineDash([8, 12])
  ctx.beginPath()
  const sl = GEO_FEATURES.shippingLane
  const [sl0x, sl0y] = toScreen(sl[0])
  ctx.moveTo(sl0x, sl0y)
  for (let i = 1; i < sl.length; i++) {
    const [slx, sly] = toScreen(sl[i])
    ctx.lineTo(slx, sly)
  }
  ctx.stroke()
  ctx.setLineDash([])

  // MCM ZB-Alpha corridor (cyan)
  ctx.strokeStyle = 'rgba(34,211,238,0.5)'
  ctx.lineWidth = 3
  ctx.setLineDash([6, 4])
  ctx.beginPath()
  const mcm = GEO_FEATURES.mcmZbAlpha
  const [m0x, m0y] = toScreen(mcm[0])
  ctx.moveTo(m0x, m0y)
  for (let i = 1; i < mcm.length; i++) {
    const [mx, my] = toScreen(mcm[i])
    ctx.lineTo(mx, my)
  }
  ctx.stroke()
  ctx.setLineDash([])
  // MCM label
  const [mlx, mly] = toScreen(mcm[1])
  ctx.fillStyle = 'rgba(34,211,238,0.7)'
  ctx.font = 'bold 9px "JetBrains Mono", monospace'
  ctx.fillText('ZB-ALPHA MCM', mlx + 5, mly - 6)

  // SAM threat rings
  for (const [lon, lat, radDeg, label] of GEO_FEATURES.samRings) {
    const center = geoToCanvas(lon, lat)
    const edge   = geoToCanvas(lon + radDeg, lat)
    const cx = center.x * w
    const cy = center.y * h
    const r = Math.abs(edge.x - center.x) * w
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.strokeStyle = 'rgba(234,179,8,0.25)'
    ctx.lineWidth = 1
    ctx.setLineDash([3, 5])
    ctx.stroke()
    ctx.setLineDash([])
    ctx.fillStyle = 'rgba(234,179,8,0.45)'
    ctx.font = '7px "JetBrains Mono", monospace'
    ctx.fillText(label, cx - r * 0.6, cy - r - 3)
  }

  // Airbase markers
  for (const [lon, lat, label, side] of GEO_FEATURES.airbases) {
    const pt = geoToCanvas(lon, lat)
    const ax = pt.x * w
    const ay = pt.y * h
    if (ax < 0 || ax > w || ay < 0 || ay > h) continue
    const color = side === 'us' ? 'rgba(34,211,238,0.8)' : 'rgba(248,113,113,0.8)'
    // Draw runway symbol (small rectangle)
    ctx.save()
    ctx.strokeStyle = color
    ctx.lineWidth = 1.5
    ctx.strokeRect(ax - 5, ay - 2, 10, 4)
    ctx.fillStyle = color
    ctx.font = '7px "JetBrains Mono", monospace'
    ctx.fillText(label, ax + 8, ay + 3)
    ctx.restore()
  }

  // Horizon line (Hormuz narrows)
  const h1 = geoToCanvas(56.4, 27.0)
  const h2 = geoToCanvas(56.4, 26.0)
  ctx.strokeStyle = 'rgba(239,68,68,0.5)'
  ctx.lineWidth = 1.5
  ctx.setLineDash([4, 4])
  ctx.beginPath()
  ctx.moveTo(h1.x * w, h1.y * h)
  ctx.lineTo(h2.x * w, h2.y * h)
  ctx.stroke()
  ctx.setLineDash([])
  ctx.fillStyle = 'rgba(239,68,68,0.6)'
  ctx.font = 'bold 8px "JetBrains Mono", monospace'
  ctx.fillText('HORMUZ CLOSURE LINE', h1.x * w + 4, h1.y * h - 3)

  // Geographic labels
  for (const [lon, lat, text] of GEO_FEATURES.labels) {
    const pt = geoToCanvas(lon, lat)
    const lx = pt.x * w
    const ly = pt.y * h
    if (lx < 0 || lx > w || ly < 0 || ly > h) continue
    ctx.fillStyle = 'rgba(161,161,170,0.45)'
    ctx.font = text.includes('GULF') || text.includes('STRAIT') || text.includes('OMAN')
      ? 'bold 10px "JetBrains Mono", monospace'
      : '8px "JetBrains Mono", monospace'
    ctx.fillText(text, lx, ly)
  }

  // Compass
  ctx.fillStyle = 'rgba(16,185,129,0.6)'
  ctx.font = 'bold 10px "JetBrains Mono", monospace'
  ctx.fillText('N ↑', w - 30, 18)

  // Scale bar
  ctx.strokeStyle = 'rgba(16,185,129,0.4)'
  ctx.lineWidth = 1.5
  // ~100nm = ~1.85° lon at this lat → approximate 100nm in canvas units
  const scaleLeft  = w - 140
  const scaleRight = w - 60
  const scaleY     = h - 14
  ctx.beginPath()
  ctx.moveTo(scaleLeft, scaleY)
  ctx.lineTo(scaleRight, scaleY)
  ctx.stroke()
  ctx.fillStyle = 'rgba(16,185,129,0.5)'
  ctx.font = '7px "JetBrains Mono", monospace'
  ctx.fillText('~100 NM', scaleLeft, scaleY - 3)
}

function drawAirTrack(ctx: CanvasRenderingContext2D, t: AirTrack, w: number, h: number, tick: number) {
  const x = t.x * w
  const y = t.y * h
  const color = AIR_COLOR[t.iff]

  ctx.save()
  ctx.shadowColor = color
  ctx.shadowBlur = t.iff === 'hostile' ? 10 : 6

  // Heading indicator
  const angle = Math.atan2(t.vy, t.vx)
  const leadLen = 16
  ctx.strokeStyle = color
  ctx.lineWidth = 1
  ctx.setLineDash([2, 3])
  ctx.beginPath()
  ctx.moveTo(x, y)
  ctx.lineTo(x + Math.cos(angle) * leadLen, y + Math.sin(angle) * leadLen)
  ctx.stroke()
  ctx.setLineDash([])

  // Symbol
  if (t.iff === 'friend') {
    // STANAG friendly air = circle (blue)
    ctx.strokeStyle = color
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.arc(x, y, t.kind === 'bomber' ? 7 : t.kind === 'awacs' || t.kind === 'tanker' ? 6 : 5, 0, Math.PI * 2)
    ctx.stroke()
    // Center dot
    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(x, y, 2, 0, Math.PI * 2)
    ctx.fill()
  } else {
    // Hostile = diamond (red) pulsing
    const pulse = t.iff === 'hostile' && tick % 60 < 30 ? 1.3 : 1.0
    const r = 5 * pulse
    ctx.strokeStyle = color
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.moveTo(x, y - r)
    ctx.lineTo(x + r, y)
    ctx.lineTo(x, y + r)
    ctx.lineTo(x - r, y)
    ctx.closePath()
    ctx.stroke()
    ctx.fillStyle = `${color}33`
    ctx.fill()
  }

  // Label
  ctx.shadowBlur = 0
  ctx.fillStyle = color
  ctx.font = '7px "JetBrains Mono", monospace'
  ctx.fillText(t.callsign, x + 8, y - 3)
  ctx.fillStyle = `${color}88`
  ctx.fillText(`FL${Math.round(t.alt / 100).toString().padStart(3, '0')}`, x + 8, y + 5)

  ctx.restore()
}

function drawMarTrack(ctx: CanvasRenderingContext2D, t: MarTrack, w: number, h: number, tick: number) {
  const x = t.x * w
  const y = t.y * h
  if (x < -20 || x > w + 20 || y < -20 || y > h + 20) return

  const color = MAR_COLOR[t.iff]

  ctx.save()
  ctx.shadowColor = color
  ctx.shadowBlur = t.iff === 'hostile' ? 8 : 5

  if (t.kind === 'mine') {
    // Diamond — pulsing red
    const pulse = tick % 80 < 40 ? 1.2 : 0.9
    const r = 4 * pulse
    ctx.strokeStyle = color
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.moveTo(x, y - r); ctx.lineTo(x + r, y)
    ctx.lineTo(x, y + r); ctx.lineTo(x - r, y)
    ctx.closePath()
    ctx.stroke()
    ctx.fillStyle = `${color}44`
    ctx.fill()
  } else if (t.kind === 'carrier') {
    // Large rectangle
    ctx.strokeStyle = color
    ctx.lineWidth = 2
    ctx.strokeRect(x - 10, y - 4, 20, 8)
    // Superstructure dot
    ctx.fillStyle = color
    ctx.fillRect(x + 5, y - 4, 3, 4)
  } else if (t.kind === 'ssn' || t.kind === 'ssgn') {
    // Elongated ellipse
    ctx.strokeStyle = color
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.ellipse(x, y, 9, 4, 0, 0, Math.PI * 2)
    ctx.stroke()
    ctx.fillStyle = `${color}22`
    ctx.fill()
  } else if (t.kind === 'irgc_fac') {
    // Small triangle pointing in direction of motion
    const angle = Math.atan2(t.vy, t.vx)
    const r = 5
    ctx.strokeStyle = color
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.moveTo(x + Math.cos(angle) * r, y + Math.sin(angle) * r)
    ctx.lineTo(x + Math.cos(angle + 2.4) * r, y + Math.sin(angle + 2.4) * r)
    ctx.lineTo(x + Math.cos(angle - 2.4) * r, y + Math.sin(angle - 2.4) * r)
    ctx.closePath()
    ctx.stroke()
    ctx.fillStyle = `${color}44`
    ctx.fill()
  } else if (t.kind === 'irgc_sub') {
    ctx.strokeStyle = color
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.ellipse(x, y, 7, 3, 0, 0, Math.PI * 2)
    ctx.stroke()
  } else {
    // Generic circle
    const r = t.kind === 'ddg' ? 5 : t.kind === 'mcm' ? 4 : t.kind === 'tanker_civ' ? 4 : 4
    ctx.strokeStyle = color
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.stroke()
    if (t.iff === 'friend') {
      ctx.fillStyle = `${color}22`
      ctx.fill()
    }
  }

  // Speed leader
  if (t.sog > 0 && t.kind !== 'mine') {
    const angle = Math.atan2(t.vy, t.vx)
    ctx.strokeStyle = `${color}55`
    ctx.lineWidth = 0.75
    ctx.setLineDash([2, 3])
    ctx.beginPath()
    ctx.moveTo(x, y)
    ctx.lineTo(x + Math.cos(angle) * 14, y + Math.sin(angle) * 14)
    ctx.stroke()
    ctx.setLineDash([])
  }

  // Label
  ctx.shadowBlur = 0
  ctx.fillStyle = color
  ctx.font = '7px "JetBrains Mono", monospace'
  ctx.fillText(t.name, x + 9, y - 2)
  if (t.mmsi) {
    ctx.fillStyle = `${color}66`
    ctx.fillText(`AIS:${t.mmsi}`, x + 9, y + 5)
  }

  ctx.restore()
}

// ── Intercept engagement arcs ───────────────────────────────────────────────────
function drawEngagementArcs(
  ctx: CanvasRenderingContext2D,
  tracks: AirTrack[],
  W: number,
  H: number,
  tick: number
) {
  const hostiles  = tracks.filter((t) => t.iff === 'hostile')
  const friendFighters = tracks.filter((t) => t.iff === 'friend' && (t.kind === 'fighter' || t.kind === 'uav'))

  for (const hostile of hostiles) {
    // Find closest friendly fighter
    let nearest: AirTrack | null = null
    let minDist = Infinity
    for (const f of friendFighters) {
      const d = Math.hypot(f.x - hostile.x, f.y - hostile.y)
      if (d < minDist) { minDist = d; nearest = f }
    }
    if (!nearest || minDist > 0.45) continue

    const hx = hostile.x * W
    const hy = hostile.y * H
    const fx = nearest.x * W
    const fy = nearest.y * H

    // Curved intercept arc (quadratic control point biased laterally)
    const mx = (hx + fx) / 2
    const my = (hy + fy) / 2
    const perpX = -(fy - hy) * 0.25
    const perpY =  (fx - hx) * 0.25

    const alpha = 0.3 + 0.2 * Math.sin(tick * 0.06)
    ctx.save()
    ctx.strokeStyle = `rgba(250,204,21,${alpha})`  // yellow intercept
    ctx.lineWidth = 1
    ctx.setLineDash([4, 5])
    ctx.shadowColor = 'rgba(250,204,21,0.4)'
    ctx.shadowBlur = 4
    ctx.beginPath()
    ctx.moveTo(fx, fy)
    ctx.quadraticCurveTo(mx + perpX, my + perpY, hx, hy)
    ctx.stroke()
    ctx.setLineDash([])

    // Pulsing intercept datum ring on hostile
    const ringR = 12 + 4 * Math.sin(tick * 0.08)
    ctx.beginPath()
    ctx.arc(hx, hy, ringR, 0, Math.PI * 2)
    ctx.strokeStyle = `rgba(239,68,68,${0.2 + 0.15 * Math.sin(tick * 0.07)})`
    ctx.lineWidth = 0.75
    ctx.setLineDash([2, 4])
    ctx.stroke()
    ctx.setLineDash([])

    ctx.restore()
  }
}

// ── Layer toggles ──────────────────────────────────────────────────────────────
interface Layers {
  air: boolean
  maritime: boolean
  mines: boolean
  ais: boolean
  sam: boolean
  labels: boolean
}

// ── Main component ─────────────────────────────────────────────────────────────
export function C2Canvas() {
  const canvasRef   = useRef<HTMLCanvasElement>(null)
  const airRef      = useRef<AirTrack[]>(createAirTracks())
  const marRef      = useRef<MarTrack[]>(createMarTracks())
  const animRef     = useRef<number | null>(null)
  const tickRef     = useRef(0)
  const [running, setRunning]   = useState(true)
  const [layers, setLayers]     = useState<Layers>({ air: true, maritime: true, mines: true, ais: true, sam: true, labels: true })
  const [selected, setSelected] = useState<string | null>(null)
  const [tooltip, setTooltip]   = useState<{ x: number; y: number; text: string[] } | null>(null)

  const toggleLayer = (key: keyof Layers) =>
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }))

  const drawFrame = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const W = canvas.width
    const H = canvas.height
    const tick = tickRef.current++

    // Update positions (wrap at edges in normalized space)
    airRef.current = airRef.current.map((t) => {
      const nx = t.x + t.vx
      const ny = t.y + t.vy
      let nvx = t.vx, nvy = t.vy
      if (nx < 0.01 || nx > 0.99) nvx = -nvx
      if (ny < 0.02 || ny > 0.98) nvy = -nvy
      return { ...t, x: Math.max(0.01, Math.min(0.99, nx)), y: Math.max(0.02, Math.min(0.98, ny)), vx: nvx, vy: nvy }
    })
    marRef.current = marRef.current.map((t) => {
      if (t.sog === 0) return t
      const nx = t.x + t.vx
      const ny = t.y + t.vy
      let nvx = t.vx, nvy = t.vy
      if (nx < 0.01 || nx > 0.99) nvx = -nvx
      if (ny < 0.02 || ny > 0.98) nvy = -nvy
      return { ...t, x: Math.max(0.01, Math.min(0.99, nx)), y: Math.max(0.02, Math.min(0.98, ny)), vx: nvx, vy: nvy }
    })

    // Draw
    drawGeoBackground(ctx, W, H)

    if (layers.maritime) {
      for (const t of marRef.current) {
        if (!layers.mines && t.kind === 'mine') continue
        if (!layers.ais   && t.kind === 'tanker_civ') continue
        drawMarTrack(ctx, t, W, H, tick)
      }
    }

    if (layers.air) {
      for (const t of airRef.current) {
        drawAirTrack(ctx, t, W, H, tick)
      }
      drawEngagementArcs(ctx, airRef.current, W, H, tick)
    }

    // Selected highlight
    if (selected) {
      const allTracks = [...airRef.current, ...marRef.current]
      const trk = allTracks.find((t) => t.id === selected)
      if (trk) {
        const sx = trk.x * W
        const sy = trk.y * H
        ctx.save()
        ctx.strokeStyle = 'rgba(255,255,100,0.6)'
        ctx.lineWidth = 1.5
        ctx.setLineDash([3, 3])
        ctx.beginPath()
        ctx.arc(sx, sy, 14, 0, Math.PI * 2)
        ctx.stroke()
        ctx.setLineDash([])
        ctx.restore()
      }
    }

    // HUD overlay — timestamp
    ctx.fillStyle = 'rgba(16,185,129,0.5)'
    ctx.font = '8px "JetBrains Mono", monospace'
    const now = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'UTC' })
    ctx.fillText(`${toDTG(getConflictDay())} · UTC ${now} · DAY ${getConflictDay()}`, 8, 14)
    ctx.fillText('JADC2 COP · PGDR-1 · CENTCOM AOR', 8, H - 6)
  }, [layers, selected])

  const startLoop = useCallback(() => {
    const loop = () => { drawFrame(); animRef.current = requestAnimationFrame(loop) }
    animRef.current = requestAnimationFrame(loop)
  }, [drawFrame])

  const stopLoop = useCallback(() => {
    if (animRef.current !== null) { cancelAnimationFrame(animRef.current); animRef.current = null }
  }, [])

  useEffect(() => {
    if (running) startLoop(); else stopLoop()
    return stopLoop
  }, [running, startLoop, stopLoop])

  // Click to identify track
  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width  / rect.width
    const scaleY = canvas.height / rect.height
    const cx = (e.clientX - rect.left) * scaleX
    const cy = (e.clientY - rect.top)  * scaleY
    const W = canvas.width
    const H = canvas.height

    let nearest: string | null = null
    let minDist = 18

    for (const t of airRef.current) {
      const d = Math.hypot(t.x * W - cx, t.y * H - cy)
      if (d < minDist) { minDist = d; nearest = t.id }
    }
    for (const t of marRef.current) {
      const d = Math.hypot(t.x * W - cx, t.y * H - cy)
      if (d < minDist) { minDist = d; nearest = t.id }
    }

    if (nearest) {
      setSelected(nearest)
      const allTracks = [...airRef.current, ...marRef.current]
      const trk = allTracks.find((t) => t.id === nearest)!
      const lines: string[] = []
      if ('callsign' in trk) {
        const a = trk as AirTrack
        lines.push(`CALLSIGN: ${a.callsign}`, `IFF: ${a.iff.toUpperCase()}`, `ALT: FL${Math.round(a.alt / 100).toString().padStart(3,'0')}`, `SPD: ${a.speed}kts`, `MODE-C: ${a.mode}`)
      } else {
        const m = trk as MarTrack
        lines.push(`VESSEL: ${m.name}`, `IFF: ${m.iff.toUpperCase()}`, `HDG: ${m.hdg}°`, `SOG: ${m.sog}kts`)
        if (m.mmsi) lines.push(`MMSI: ${m.mmsi}`)
      }
      const canvasRect = canvas.getBoundingClientRect()
      const trkScreenX = (trk.x * W / scaleX) + canvasRect.left - rect.left
      const trkScreenY = (trk.y * H / scaleY) + canvasRect.top  - rect.top
      setTooltip({ x: trkScreenX, y: trkScreenY, text: lines })
    } else {
      setSelected(null)
      setTooltip(null)
    }
  }

  const handleReset = () => {
    airRef.current = createAirTracks()
    marRef.current = createMarTracks()
    setSelected(null); setTooltip(null)
  }

  const layerButtons: { key: keyof Layers; label: string; color: string }[] = [
    { key: 'air',      label: 'AIR',     color: 'border-cyan-800 text-cyan-400 data-[active]:bg-cyan-950' },
    { key: 'maritime', label: 'MARITIME',color: 'border-emerald-800 text-emerald-400 data-[active]:bg-emerald-950' },
    { key: 'mines',    label: 'MINES',   color: 'border-red-900 text-red-400 data-[active]:bg-red-950' },
    { key: 'ais',      label: 'AIS',     color: 'border-amber-800 text-amber-400 data-[active]:bg-amber-950' },
    { key: 'sam',      label: 'SAM',     color: 'border-yellow-800 text-yellow-400 data-[active]:bg-yellow-950' },
  ]

  return (
    <div className="space-y-3">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => setRunning((v) => !v)}
          className="flex items-center gap-2 px-4 min-h-[40px] text-xs tracking-widest border border-emerald-800 rounded-lg text-emerald-400 hover:bg-emerald-950/50 active:scale-95 transition-all duration-150"
        >
          {running ? <Pause size={14} /> : <Play size={14} />}
          {running ? 'PAUSE' : 'PLAY'}
        </button>
        <button
          onClick={handleReset}
          className="flex items-center gap-2 px-4 min-h-[40px] text-xs tracking-widest border border-zinc-700 rounded-lg text-zinc-400 hover:border-zinc-500 active:scale-95 transition-all duration-150"
        >
          <RotateCcw size={14} /> RESET
        </button>
        <span className="text-[9px] text-zinc-600 tracking-widest ml-1 flex items-center gap-1">
          <Radio size={9} /> {running ? '● LV' : '■ PAUSED'}
        </span>
        <div className="flex-1" />
        {layerButtons.map(({ key, label, color }) => (
          <button
            key={key}
            data-active={layers[key] ? '' : undefined}
            onClick={() => toggleLayer(key)}
            className={`px-3 min-h-[36px] text-[9px] tracking-widest border rounded-lg transition-all duration-150 active:scale-95 ${color} ${layers[key] ? 'opacity-100' : 'opacity-40'}`}
          >
            <Layers size={8} className="inline mr-1" />{label}
          </button>
        ))}
      </div>

      {/* Canvas */}
      <div className="relative border border-emerald-900/60 rounded-sm overflow-hidden"
           style={{ boxShadow: '0 0 30px rgba(16,185,129,0.07)' }}>
        <canvas
          ref={canvasRef}
          width={1000}
          height={580}
          className="w-full block bg-zinc-950 cursor-crosshair"
          style={{ maxHeight: '580px' }}
          onClick={handleClick}
          role="img"
          aria-label="JADC2 Combined Operations Picture — Persian Gulf / Arabian Sea"
        />

        {/* Tooltip overlay */}
        {tooltip && (
          <div
            className="absolute pointer-events-none z-10 bg-zinc-950/95 border border-cyan-900 rounded-sm px-2.5 py-2 text-[10px] font-mono text-cyan-300 space-y-0.5 shadow-xl"
            style={{ left: tooltip.x + 10, top: Math.max(8, tooltip.y - 20) }}
          >
            {tooltip.text.map((line, i) => <div key={i}>{line}</div>)}
            <div className="text-zinc-600 text-[8px] pt-0.5 border-t border-zinc-800">CLICK ELSEWHERE TO DISMISS</div>
          </div>
        )}
      </div>

      {/* Legend row */}
      <div className="flex flex-wrap gap-4 text-[9px] text-zinc-500 tracking-widest pt-1">
        <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded-full border border-cyan-400" /> FRIEND AIR</span>
        <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-3 border border-red-400 rotate-45" /> HOSTILE AIR</span>
        <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded-full border border-emerald-400" /> FRIEND SURFACE</span>
        <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-3 border border-red-500 rotate-45" /> IRGC/MINE</span>
        <span className="flex items-center gap-1.5"><span className="inline-block w-2 h-2 border border-amber-400 rounded-full" /> AIS CIVIL</span>
        <span className="flex items-center gap-1.5 text-cyan-400/60">— ZB-ALPHA MCM LANE</span>
        <span className="flex items-center gap-1.5 text-amber-400/40">— SHIPPING LANE (CLOSED)</span>
        <span className="flex items-center gap-1.5 text-yellow-400/50">○ SAM THREAT RING</span>
        <span className="flex items-center gap-1.5">□ AIRBASE</span>
      </div>
    </div>
  )
}
