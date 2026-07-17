import { C2Canvas } from '@/components/C2Canvas'
import { Radio, Globe2, Wind, Anchor, AlertTriangle, ExternalLink, Cpu } from 'lucide-react'
import { getConflictDay, toDTG } from '@/lib/conflict-day'
import { OraclePanel } from '@/components/OraclePanel'
import { LiveNewsBoard } from '@/components/LiveNewsBoard'
import { createServerClient } from '@/lib/supabase-server'

export const revalidate = 0

const CONFLICT_DAY = getConflictDay()

// ── Air track watch list (static display) — DAY 22 ──────────────────────────
const AIR_TRACKS = [
  // ── Friendly fast air ──
  { id: 'a01', callsign: 'VIPER-11',    type: 'F-35A Lightning II', iff: 'FRIEND', alt: 'FL250', hdg: '285°', spd: '480kt', origin: 'Al Dhafra AB',   status: 'CAP HOZ' },
  { id: 'a02', callsign: 'VIPER-12',    type: 'F-35A Lightning II', iff: 'FRIEND', alt: 'FL248', hdg: '285°', spd: '490kt', origin: 'Al Dhafra AB',   status: 'CAP HOZ' },
  { id: 'a03', callsign: 'VIPER-13',    type: 'F-35A Lightning II', iff: 'FRIEND', alt: 'FL252', hdg: '110°', spd: '475kt', origin: 'Al Dhafra AB',   status: 'ESCORT' },
  { id: 'a04', callsign: 'HORNET-21',   type: 'F/A-18E Super Hornet',iff: 'FRIEND', alt: 'FL220', hdg: '075°', spd: '510kt', origin: 'CVN-71 TR',     status: 'STRIKE RTN' },
  { id: 'a05', callsign: 'HORNET-22',   type: 'F/A-18E Super Hornet',iff: 'FRIEND', alt: 'FL215', hdg: '075°', spd: '505kt', origin: 'CVN-71 TR',     status: 'STRIKE RTN' },
  { id: 'a06', callsign: 'HORNET-31',   type: 'F/A-18F Super Hornet',iff: 'FRIEND', alt: 'FL230', hdg: '085°', spd: '520kt', origin: 'CVN-69 IKE',    status: 'RTB' },
  { id: 'a07', callsign: 'RAPTOR-31',   type: 'F-22A Raptor',       iff: 'FRIEND', alt: 'FL350', hdg: '190°', spd: '550kt', origin: 'Al Udeid AB',    status: 'DCA SWEEP' },
  { id: 'a08', callsign: 'RAPTOR-32',   type: 'F-22A Raptor',       iff: 'FRIEND', alt: 'FL355', hdg: '185°', spd: '545kt', origin: 'Al Udeid AB',    status: 'DCA SWEEP' },
  { id: 'a09', callsign: 'TYPHOON-1',   type: 'Typhoon FGR4',       iff: 'FRIEND', alt: 'FL280', hdg: '105°', spd: '520kt', origin: 'Al Udeid AB',    status: 'ESCORT' },
  { id: 'a10', callsign: 'RAFALE-11',   type: 'Rafale M',           iff: 'FRIEND', alt: 'FL260', hdg: '260°', spd: '495kt', origin: 'FS CDG R91',     status: 'CAP' },
  { id: 'a11', callsign: 'RAFALE-12',   type: 'Rafale M',           iff: 'FRIEND', alt: 'FL262', hdg: '260°', spd: '500kt', origin: 'FS CDG R91',     status: 'CAP' },
  { id: 'a12', callsign: 'FALCON-41',   type: 'F-16C Block 52+',    iff: 'FRIEND', alt: 'FL200', hdg: '150°', spd: '500kt', origin: 'Muwaffaq Salti',  status: 'CAS READY' },
  { id: 'a13', callsign: 'FALCON-42',   type: 'F-16C Block 52+',    iff: 'FRIEND', alt: 'FL205', hdg: '145°', spd: '505kt', origin: 'Muwaffaq Salti',  status: 'CAS READY' },
  // ── Stealth strike ──
  { id: 'a14', callsign: 'SPIRIT-01',   type: 'B-2A Spirit',        iff: 'FRIEND', alt: 'FL450', hdg: '230°', spd: '400kt', origin: 'Diego Garcia',   status: 'RTB' },
  { id: 'a15', callsign: 'ANVIL-01',    type: 'B-21 Raider',        iff: 'FRIEND', alt: 'FL510', hdg: '340°', spd: '410kt', origin: 'Diego Garcia',   status: 'EGRESS — COMBAT DEBUT' },
  // ── Tankers / C2 ──
  { id: 'a16', callsign: 'TEXACO-1',    type: 'KC-135R Stratotanker',iff: 'FRIEND', alt: 'FL280', hdg: '080°', spd: '310kt', origin: 'Al Udeid AB',   status: 'ORBIT AAR' },
  { id: 'a17', callsign: 'TEXACO-2',    type: 'KC-135R Stratotanker',iff: 'FRIEND', alt: 'FL270', hdg: '260°', spd: '305kt', origin: 'Al Udeid AB',   status: 'ORBIT AAR' },
  { id: 'a18', callsign: 'TEXACO-3',    type: 'KC-46A Pegasus',     iff: 'FRIEND', alt: 'FL285', hdg: '070°', spd: '320kt', origin: 'Al Dhafra AB',   status: 'ORBIT AAR' },
  { id: 'a19', callsign: 'SENTRY-11',   type: 'E-3G Sentry AWACS',  iff: 'FRIEND', alt: 'FL300', hdg: '070°', spd: '290kt', origin: 'Al Udeid AB',    status: 'ON-STATION' },
  { id: 'a20', callsign: 'WEDGETAIL-1', type: 'E-7A Wedgetail',     iff: 'FRIEND', alt: 'FL290', hdg: '260°', spd: '285kt', origin: 'Al Udeid AB',    status: 'ON-STATION' },
  { id: 'a21', callsign: 'RIVET-1',     type: 'RC-135W Rivet Joint', iff: 'FRIEND', alt: 'FL340', hdg: '090°', spd: '280kt', origin: 'Al Udeid AB',   status: 'SIGINT ORBIT' },
  // ── ISR / UAS ──
  { id: 'a22', callsign: 'HAWK-01',     type: 'RQ-4B Global Hawk',  iff: 'FRIEND', alt: 'FL540', hdg: '220°', spd: '310kt', origin: 'Al Dhafra AB',   status: 'ISR LOITER' },
  { id: 'a23', callsign: 'HAWK-02',     type: 'RQ-4B Global Hawk',  iff: 'FRIEND', alt: 'FL545', hdg: '215°', spd: '315kt', origin: 'Al Dhafra AB',   status: 'ISR LOITER' },
  { id: 'a24', callsign: 'MQ9-01',      type: 'MQ-9A Reaper',       iff: 'FRIEND', alt: 'FL250', hdg: '130°', spd: '230kt', origin: 'Al Udeid AB',    status: 'HVI TRACK' },
  { id: 'a25', callsign: 'MQ9-02',      type: 'MQ-9A Reaper',       iff: 'FRIEND', alt: 'FL245', hdg: '135°', spd: '225kt', origin: 'Camp Lemonnier', status: 'BDA ISR' },
  { id: 'a26', callsign: 'CHARGER-1',   type: 'MH-60R Seahawk',     iff: 'FRIEND', alt: '100ft', hdg: '080°', spd: '130kt', origin: 'CVN-71 TR',      status: 'ASW' },
  { id: 'a27', callsign: 'CHARGER-2',   type: 'MH-60R Seahawk',     iff: 'FRIEND', alt: '80ft',  hdg: '265°', spd: '125kt', origin: 'DDG-107',        status: 'ASW — HORMUZ APPROACH PATROL' },
  // ── IRGCAF hostile tracks ──
  { id: 'h01', callsign: 'BANDIT-α',    type: 'F-14D Tomcat',       iff: 'HOSTILE', alt: '—',     hdg: '—',    spd: '—',    origin: 'Bandar Abbas',   status: 'DESTROYED D21' },
  { id: 'h02', callsign: 'BANDIT-β',    type: 'F-14D Tomcat',       iff: 'HOSTILE', alt: '—',     hdg: '—',    spd: '—',    origin: 'Bandar Abbas',   status: 'DESTROYED D21' },
  { id: 'h03', callsign: 'BANDIT-γ',    type: 'Su-25K Frogfoot',    iff: 'HOSTILE', alt: 'FL080', hdg: '210°', spd: '380kt', origin: 'Bandar Abbas',   status: 'AIRBORNE — MONITOR' },
  { id: 'h04', callsign: 'BANDIT-δ',    type: 'Su-25K Frogfoot',    iff: 'HOSTILE', alt: 'FL075', hdg: '215°', spd: '375kt', origin: 'Bandar Abbas',   status: 'AIRBORNE — MONITOR' },
  { id: 'h05', callsign: 'SHAD-04',     type: 'Shahed-136 UCAV',    iff: 'HOSTILE', alt: '4,200', hdg: '240°', spd: '112kt', origin: 'Jask AB (est)',  status: 'INBOUND' },
  { id: 'h06', callsign: 'SHAD-05',     type: 'Shahed-136 UCAV',    iff: 'HOSTILE', alt: '4,500', hdg: '235°', spd: '108kt', origin: 'Jask AB (est)',  status: 'INBOUND' },
  { id: 'h07', callsign: 'SHAD-06',     type: 'Shahed-136 UCAV',    iff: 'HOSTILE', alt: '4,100', hdg: '238°', spd: '115kt', origin: 'Jask AB (est)',  status: 'INBOUND' },
  { id: 'h08', callsign: 'SHAD-07',     type: 'Shahed-136 UCAV',    iff: 'HOSTILE', alt: '4,600', hdg: '242°', spd: '110kt', origin: 'Jask AB (est)',  status: 'INBOUND' },
  { id: 'h09', callsign: 'FATEH-TRACK', type: 'Fateh-110 SRBM',     iff: 'HOSTILE', alt: 'BMT',   hdg: '220°', spd: 'MACH5', origin: 'Tabriz Site-7',  status: '⚠ LAUNCH DETECT' },
]

// ── Maritime track watch list — DAY 22 ─────────────────────────────────────────
const MAR_TRACKS = [
  // ── US Navy ──
  { id: 'm01', name: 'CVN-71 T. ROOSEVELT', type: 'CV/CVW-1 (Nimitz)',  mmsi: '369012002', pos: '14.5°N 43.5°E', hdg: '010°', sog: '10kt', status: 'RED SEA STRIKE OPS',   iff: 'FRIEND' },
  { id: 'm02', name: 'CVN-72 ABE LINCOLN',  type: 'CV/CVW-3 (Nimitz)',  mmsi: '369012003', pos: '23.5°N 60.8°E', hdg: '280°', sog: '14kt', status: 'ARABIAN SEA STRIKE',   iff: 'FRIEND' },
  { id: 'm03', name: 'CVN-69 EISENHOWER',   type: 'CV/CVW-7 (Nimitz)',  mmsi: '369012001', pos: '24.0°N 59.0°E', hdg: '270°', sog: '12kt', status: 'GOM STRIKE OPS',       iff: 'FRIEND' },
  { id: 'm04', name: 'DDG-107 GRAVELY',     type: 'DDG Arleigh Burke',   mmsi: '369112107', pos: '25.2°N 57.5°E', hdg: '255°', sog: '15kt', status: 'SAG AAW SCREEN',       iff: 'FRIEND' },
  { id: 'm06', name: 'DDG-80 TR COLE',      type: 'DDG Arleigh Burke',   mmsi: '369108000', pos: '23.8°N 58.8°E', hdg: '265°', sog: '12kt', status: 'SAG SCREEN',           iff: 'FRIEND' },
  { id: 'm07', name: 'CG-55 LEYTE GULF',    type: 'CG Ticonderoga',      mmsi: '369005500', pos: '24.3°N 57.8°E', hdg: '260°', sog: '14kt', status: 'AAW PICKET — SM-3',    iff: 'FRIEND' },
  { id: 'm08', name: 'LPD-17 SAN ANTONIO',  type: 'LPD Amphib',          mmsi: '369001700', pos: '23.0°N 59.5°E', hdg: '275°', sog: '11kt', status: 'CSAR / NEO READY',     iff: 'FRIEND' },
  { id: 'm09', name: 'SSGN-729 GEORGIA',    type: 'SSGN Ohio-class',     mmsi: '—',         pos: '24.5°N 57.8°E', hdg: '210°', sog: '6kt',  status: 'TLAM AWAITING TASKING',iff: 'FRIEND' },
  { id: 'm10', name: 'SSN-774 VIRGINIA',    type: 'SSN Virginia-class',  mmsi: '—',         pos: '25.8°N 56.0°E', hdg: '070°', sog: '8kt',  status: 'W-HOZ — COVERT MCM SUPT', iff: 'FRIEND' },
  { id: 'm11', name: 'SSN-777 N. CAROLINA', type: 'SSN Virginia-class',  mmsi: '—',         pos: '25.5°N 56.8°E', hdg: '190°', sog: '7kt',  status: 'SOZ — GOLF-7 INACTIVE — BANDAR APPROACHES PATROL', iff: 'FRIEND' },
  { id: 'm12', name: 'MCM-14 CHIEF',        type: 'MCM Avenger-class',   mmsi: '369001401', pos: '26.1°N 56.3°E', hdg: '065°', sog: '4kt',  status: 'ZB-ALPHA ACTIVE MCM',  iff: 'FRIEND' },
  { id: 'm13', name: 'MCM-11 GLADIATOR',    type: 'MCM Avenger-class',   mmsi: '369001101', pos: '26.0°N 56.5°E', hdg: '070°', sog: '4kt',  status: 'ZB-ALPHA ACTIVE MCM',  iff: 'FRIEND' },
  // ── Coalition ──
  { id: 'm14', name: 'D34 HMS DIAMOND',      type: 'T45 DDG (Royal Navy)',mmsi: '234567890', pos: '14.8°N 44.0°E', hdg: '355°', sog: '14kt', status: 'RED SEA AAW',          iff: 'FRIEND' },
  { id: 'm15', name: 'HMAS HOBART (DDH-39)', type: 'Hobart-class DDG',   mmsi: '503012039', pos: '23.2°N 60.2°E', hdg: '285°', sog: '13kt', status: 'ARABIAN SEA SCREEN',   iff: 'FRIEND' },
  { id: 'm16', name: 'R91 FS CDG',           type: 'CV Carrier Group',   mmsi: '226000001', pos: '23.0°N 60.5°E', hdg: '280°', sog: '11kt', status: 'ARABIAN SEA STRIKE',   iff: 'FRIEND' },
  { id: 'm17', name: 'F85 FS PROVENCE',      type: 'FREMM Frigate',      mmsi: '226000085', pos: '22.8°N 60.3°E', hdg: '280°', sog: '14kt', status: 'CDG AAW SCREEN',       iff: 'FRIEND' },
  // ── IRGCN hostile ──
  { id: 'i01', name: 'IRGCN FAC-1',          type: 'Thondor FAC (ASCM)', mmsi: '—',         pos: '26.7°N 56.1°E', hdg: '220°', sog: '28kt', status: '⚠ THREAT VECTOR',     iff: 'HOSTILE' },
  { id: 'i02', name: 'IRGCN FAC-2',          type: 'Thondor FAC (ASCM)', mmsi: '—',         pos: '26.8°N 56.3°E', hdg: '215°', sog: '30kt', status: '⚠ THREAT VECTOR',     iff: 'HOSTILE' },
  { id: 'i03', name: 'IRGCN FAC-3',          type: 'Houdong FAC',        mmsi: '—',         pos: '26.9°N 56.5°E', hdg: '225°', sog: '27kt', status: '⚠ THREAT VECTOR',     iff: 'HOSTILE' },
  { id: 'i04', name: 'IRGCN FAC-4',          type: 'Houdong FAC',        mmsi: '—',         pos: '27.0°N 56.4°E', hdg: '218°', sog: '24kt', status: 'MONITOR',             iff: 'HOSTILE' },
  { id: 'i05', name: 'GOLF-7 (INACTIVE)',      type: 'Kilo-class SSK',     mmsi: '—',         pos: '26.7°N 56.3°E', hdg: '345°', sog: '3kt',  status: 'INACTIVE — Bandar Abbas inbound D26', iff: 'MONITOR' },
  { id: 'i06', name: 'GHADIR-3 (CONTACT)',    type: 'Ghadir mini-SSK',    mmsi: '—',         pos: '26.4°N 56.7°E', hdg: '155°', sog: '3kt',  status: 'P-8A TRACKING',       iff: 'HOSTILE' },
  { id: 'i07', name: 'KILO-2',               type: 'Kilo-class SSK',     mmsi: '—',         pos: '24.8°N 58.2°E', hdg: '135°', sog: '6kt',  status: 'SUSPECTED',           iff: 'HOSTILE' },
  // ── Neutral / commercial ──
  { id: 'c01', name: 'MT GULF SPIRIT',        type: 'VLCC Suezmax',       mmsi: '477123456', pos: '22.8°N 60.5°E', hdg: '095°', sog: '12kt', status: 'REROUTED — AIS ACTIVE', iff: 'NEUTRAL' },
  { id: 'c02', name: 'MT HORIZON SKY',        type: 'VLCC Aframax',       mmsi: '477654321', pos: '22.5°N 61.0°E', hdg: '270°', sog: '11kt', status: 'REROUTED — AIS ACTIVE', iff: 'NEUTRAL' },
  { id: 'c03', name: 'MT ARABIAN TRADER',     type: 'LNG Tanker',         mmsi: '566012345', pos: '21.5°N 62.0°E', hdg: '265°', sog: '13kt', status: 'DIVERTED OMAN COAST',  iff: 'NEUTRAL' },
]

// ── ROE / EMCON strip — DAY 22 ────────────────────────────────────────────────
const ROE_ITEMS = [
  { label: 'ROE',            value: 'FOXTROT (WEAPONS FREE – HOZ APZ)', color: 'text-red-400' },
  { label: 'EMCON',          value: 'DELTA (AAW-ACTIVE / LINK-16 / IFF ON)', color: 'text-amber-400' },
  { label: 'FPCON',          value: 'CHARLIE+ (THEATRE-WIDE)', color: 'text-red-400' },
  { label: 'BMD POSTURE',    value: 'ACTIVE — SM-3 Block IIA BATTERIES HOT', color: 'text-red-400' },
  { label: 'LINK16 NETID',   value: 'PGDR-1 / 12050 (CENTCOM AOR)', color: 'text-cyan-400' },
  { label: 'CSAR FREQ',      value: '282.8 MHz / ATC GUARD', color: 'text-emerald-400' },
  { label: 'ABORT CODE',     value: `KNOTTED (Day ${CONFLICT_DAY})`, color: 'text-zinc-400' },
]

// ── Airspace status ───────────────────────────────────────────────────────────
const AIRSPACE = [
  { id: 'HOZ', name: 'Hormuz Strait', status: 'NO-FLY (EXCEPT CAS)',    color: 'bg-red-900/40 border-red-800 text-red-300' },
  { id: 'PGC', name: 'Persian Gulf Ctrl',status: 'RESTRICTED – JTAC', color: 'bg-amber-900/40 border-amber-800 text-amber-300' },
  { id: 'GOM', name: 'Gulf of Oman',  status: 'OPEN – IFF MANDATORY',  color: 'bg-emerald-900/40 border-emerald-800 text-emerald-300' },
  { id: 'AUS', name: 'Arabian Sea',   status: 'OPEN – TANKERS ACTIVE', color: 'bg-emerald-900/40 border-emerald-800 text-emerald-300' },
  { id: 'YEM', name: 'Yemen FIR',     status: 'CLOSED – AAA/SAM THREAT',color: 'bg-red-900/40 border-red-800 text-red-300' },
  { id: 'OFZ', name: 'IRGCAF OFZ',   status: 'HOSTILE CONTROLLED',    color: 'bg-red-900/40 border-red-800 text-red-300' },
]

const SEVERITY_STYLE: Record<string, string> = {
  CRITICAL: 'text-red-400 bg-red-950/50 border-red-900',
  HIGH:     'text-amber-400 bg-amber-950/50 border-amber-900',
  MEDIUM:   'text-yellow-400 bg-yellow-950/50 border-yellow-900',
  INFO:     'text-zinc-400 bg-zinc-900/50 border-zinc-800',
}

// ── Sources ──────────────────────────────────────────────────────────────────
const SOURCES = [
  { label: 'AIS Maritime',      url: 'https://www.marinetraffic.com',   note: 'Real-time AIS vessel positions — Gulf region' },
  { label: 'ADS-B Exchange',    url: 'https://www.adsbexchange.com',     note: 'Crowd-sourced ADS-B air track data' },
  { label: `CENTCOM SITREP-${CONFLICT_DAY}`, url: '#',                               note: `US CENTCOM Situation Report Day ${CONFLICT_DAY} — AI-synthesized` },
  { label: 'USNI News',         url: 'https://news.usni.org',           note: 'US Naval Institute fleet disposition reporting' },
  { label: 'ISW Iran Update',   url: 'https://www.understandingwar.org',note: 'Institute for the Study of War daily updates' },
  { label: 'FlightAware',       url: 'https://www.flightaware.com',     note: 'FAA ASDI / SWIM feed — commercial air' },
  { label: 'NGA GEOINT',        url: 'https://www.nga.mil',             note: 'National Geospatial-Intelligence Agency' },
  { label: 'Open Street Map',   url: 'https://www.openstreetmap.org',   note: 'Geographic features — Persian Gulf coastline' },
]

// ── MCM corridor clearance status — DAY 22 ───────────────────────────────────
const MCM_CORRIDORS = [
  { id: 'ZB-ALPHA',  name: 'Hormuz N. Lane',   pct: 78, status: 'ACTIVE',     threat: 'D24 GOLF-7 re-seeding cleared — corridor open for VLCC escort', vessels: 'MCM-14 CHIEF, MCM-11 GLADIATOR' },
  { id: 'ZB-BETA',   name: 'Hormuz S. Lane',   pct: 45, status: 'ACTIVE',     threat: 'Pressure + moored mines; MH-53E det',       vessels: 'MH-53E DET, MH-60S' },
  { id: 'ZC-ALPHA',  name: 'Bandar Abbas Appr', pct: 0,  status: 'SUSPENDED', threat: 'IRGCN FAC + Ghadir mini-sub — DANGER',      vessels: '—' },
  { id: 'ZC-BETA',   name: 'Larak Island',     pct: 91, status: 'NEAR CLEAR', threat: 'Residual influence mines only',              vessels: 'HMS CHIDDINGFOLD' },
  { id: 'ZD-ALPHA',  name: 'Gulf of Oman W.',  pct: 99, status: 'OPEN',       threat: 'All-clear assessed — escort available',      vessels: 'MCM escort on request' },
  { id: 'ZD-BRAVO',  name: 'Gulf of Oman E.',  pct: 100,status: 'OPEN',       threat: 'Clear — HMAS HOBART TU escort',             vessels: 'HMAS HOBART DDH-39' },
]

// ── IFF color helpers ─────────────────────────────────────────────────────────
function iffColor(iff: string) {
  if (iff === 'FRIEND')  return 'text-cyan-400'
  if (iff === 'HOSTILE') return 'text-red-400'
  return 'text-amber-400'
}

function iffRowBg(iff: string) {
  if (iff === 'HOSTILE') return 'bg-red-950/20 hover:bg-red-950/30'
  return 'hover:bg-zinc-900/40'
}

export default async function CopPage() {
  // Fetch live AI-extracted scenario events from Supabase
  interface LiveScenarioEvent {
    id: number; event_id: string; time_zulu: string; type: string
    priority: string; title: string; body: string; conflict_day: number; created_at: string
  }
  interface LiveIntelEvent {
    id: string; title: string; summary: string; theater: string
    confidence: number; source_url: string; source_name: string; created_at: string
  }
  let liveEvents: LiveScenarioEvent[] = []
  let intelFallback: LiveIntelEvent[] = []
  try {
    const sb = await createServerClient()
    if (sb) {
      const [eventsRes, intelRes] = await Promise.all([
        sb.from('scenario_events')
          .select('*')
          .order('conflict_day', { ascending: false })
          .order('created_at', { ascending: false })
          .limit(20),
        sb.from('intel')
          .select('id, title, summary, theater, confidence, source_url, source_name, created_at')
          .gte('confidence', 60)
          .order('created_at', { ascending: false })
          .limit(20),
      ])
      liveEvents    = (eventsRes.data ?? []) as LiveScenarioEvent[]
      intelFallback = (intelRes.data  ?? []) as LiveIntelEvent[]
    }
  } catch { /* non-fatal */ }
  return (
    <div className="space-y-6 p-6">

      {/* Live intelligence feeds */}
      <LiveNewsBoard limit={15} warFilter={true} compact={false} />

      {/* ── Cinematic COP Masthead ── */}
      <div className="studio-masthead rounded-sm overflow-hidden">
        <div className="relative px-6 py-5">
          {/* Scanline overlay */}
          <div className="absolute inset-0 pointer-events-none z-[2]" style={{background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(16,185,129,0.015) 2px, rgba(16,185,129,0.015) 4px)'}} />

          <div className="relative z-[3] flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Globe2 size={26} className="text-emerald-400 drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                  <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full animate-pulse" />
                </div>
                <div>
                  <h1 className="text-lg font-bold tracking-widest text-emerald-400 glow-green">
                    JADC2 COMBINED OPERATIONS PICTURE
                  </h1>
                  <p className="text-[11px] text-zinc-500 tracking-wider mt-0.5">
                    PGDR-1 · CENTCOM AOR · {toDTG(CONFLICT_DAY)} · OP EPIC FURY — DAY {CONFLICT_DAY}
                  </p>
                </div>
              </div>
              <div className="text-right space-y-1">
                <div className="flex items-center gap-1.5 text-[10px] text-emerald-400/70 tracking-widest">
                  <Radio size={9} className="animate-pulse" />
                  LIVE COMPOSITE · AIS + ADS-B + LINK-16
                </div>
                <div className="on-air-badge inline-block bg-red-900/60 text-red-400 text-[8px] font-bold tracking-[0.3em] px-2.5 py-0.5 rounded-sm border border-red-800/60">
                  ● LIVE C2
                </div>
                <div className="text-[9px] text-zinc-600 mt-0.5">
                  CLASSIFICATION: TOP SECRET // NOFORN // SI-TALENT KEYHOLE
                </div>
              </div>
            </div>

            {/* ROE strip — enhanced */}
            <div className="flex flex-wrap gap-2 mt-3">
              {ROE_ITEMS.map((item) => (
                <div key={item.label} className="text-[9px] tracking-widest border border-zinc-800/80 rounded-sm px-2.5 py-1.5 bg-zinc-950/70 backdrop-blur-sm hover:border-emerald-800/60 transition-colors">
                  <span className="text-zinc-500">{item.label}: </span>
                  <span className={item.color}>{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        {/* Red accent bar */}
        <div className="studio-accent-bar" />
      </div>

      {/* Canvas — cinematic video feed frame */}
      <div className="video-feed-frame relative rounded-sm">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="hud-corners-bottom absolute inset-0 pointer-events-none z-[3]" />
        {/* Camera overlay elements */}
        <div className="absolute top-3 left-10 z-[4] flex items-center gap-2">
          <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          <span className="text-[8px] text-red-400/80 font-bold tracking-[0.25em]">REC</span>
          <span className="timecode-blink text-[8px] font-mono text-zinc-500">{toDTG(CONFLICT_DAY)}</span>
        </div>
        <div className="absolute top-3 right-10 z-[4] text-[8px] font-mono text-emerald-500/60 tracking-widest">
          CAM: THEATER-MAIN · JADC2
        </div>
        <C2Canvas />
      </div>

      {/* Airspace status — enhanced */}
      <div className="tac-card p-4 relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" style={{background: 'linear-gradient(135deg, rgba(6,182,212,0.03) 0%, transparent 50%)'}} />
        <div className="tac-section-header mb-3 relative z-[1]">
          <Wind size={14} className="text-cyan-400 drop-shadow-[0_0_6px_rgba(6,182,212,0.4)]" />
          <span className="glow-blue">AIRSPACE STATUS</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 relative z-[1]">
          {AIRSPACE.map((a) => (
            <div key={a.id} className={`border rounded-sm px-2 py-2 text-[9px] tracking-widest ${a.color} transition-all hover:scale-[1.02] hover:shadow-lg`}>
              <div className="font-bold">{a.id} — {a.name}</div>
              <div className="opacity-80 mt-0.5">{a.status}</div>
            </div>
          ))}
        </div>
      </div>

      {/* MCM Corridor Clearance — cinematic */}
      <div className="tac-card p-4 relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" style={{background: 'linear-gradient(135deg, rgba(245,158,11,0.02) 0%, transparent 50%)'}} />
        <div className="tac-section-header mb-3 relative z-[1]">
          <Anchor size={14} className="text-amber-400 drop-shadow-[0_0_6px_rgba(245,158,11,0.4)]" />
          <span className="glow-amber">MCM CORRIDOR CLEARANCE — CTF-52</span>
          <span className="text-[9px] text-zinc-600 ml-2 normal-case tracking-normal font-normal">{`NAVCENT · Day ${CONFLICT_DAY} · Hormuz + approaches`}</span>
        </div>
        <div className="space-y-3 relative z-[1]">
          {MCM_CORRIDORS.map((c) => {
            const barColor =
              c.status === 'SUSPENDED' ? 'bg-zinc-600' :
              c.pct >= 80 ? 'bg-emerald-500' :
              c.pct >= 50 ? 'bg-amber-500' : 'bg-red-500'
            const barGlow =
              c.status === 'SUSPENDED' ? '' :
              c.pct >= 80 ? 'shadow-[0_0_8px_rgba(16,185,129,0.3)]' :
              c.pct >= 50 ? 'shadow-[0_0_8px_rgba(245,158,11,0.3)]' : 'shadow-[0_0_8px_rgba(239,68,68,0.3)]'
            const statusColor =
              c.status === 'OPEN'       ? 'text-emerald-400 border-emerald-800' :
              c.status === 'NEAR CLEAR' ? 'text-sky-400 border-sky-800' :
              c.status === 'SUSPENDED'  ? 'text-zinc-500 border-zinc-700' :
                                          'text-amber-400 border-amber-800'
            return (
              <div key={c.id} className="space-y-1.5">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-[9px] font-bold text-zinc-300 tracking-widest w-20 shrink-0">{c.id}</span>
                    <span className="text-[9px] text-zinc-500 truncate">{c.name} — {c.threat}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[9px] text-zinc-600">{c.vessels}</span>
                    <span className={`text-[8px] font-bold tracking-widest border px-1.5 py-0.5 rounded-sm uppercase ${statusColor}`}>{c.status}</span>
                    <span className={`text-sm font-bold tabular-nums w-10 text-right ${c.pct >= 80 ? 'text-emerald-400' : c.pct >= 50 ? 'text-amber-400' : 'text-red-400'}`}>{c.pct}%</span>
                  </div>
                </div>
                <div className="h-2 bg-zinc-900/80 rounded-full overflow-hidden border border-zinc-800/40">
                  <div className={`h-full rounded-full transition-all duration-1000 ${barColor} ${barGlow}`} style={{ width: `${c.pct}%` }} />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Track tables — cinematic video-feed frames */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Air track table */}
        <div className="video-feed-frame tac-card p-4 relative">
          <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
          <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse" />
            <span className="text-[7px] text-cyan-500/60 font-bold tracking-[0.2em]">ADS-B LIVE</span>
          </div>
          <div className="tac-section-header mb-3 relative z-[1]">
            <Wind size={14} className="text-cyan-400 drop-shadow-[0_0_6px_rgba(6,182,212,0.4)]" />
            <span className="glow-blue">AIR TRACK PICTURE</span>
            <span className="text-[9px] text-zinc-600 ml-2 normal-case tracking-normal font-normal">ADS-B / LINK-16</span>
            <span className="ml-auto text-[9px] normal-case font-normal tracking-normal">
              <span className="text-cyan-400 font-bold">{AIR_TRACKS.filter(t => t.iff === 'FRIEND').length} FRIEND</span>
              <span className="text-zinc-600 mx-1">·</span>
              <span className="text-red-400 font-bold animate-pulse">{AIR_TRACKS.filter(t => t.iff === 'HOSTILE').length} HOSTILE</span>
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[10px] font-mono border-collapse">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 tracking-widest">
                  <th className="text-left py-1.5 pr-3">CALLSIGN</th>
                  <th className="text-left pr-3">TYPE</th>
                  <th className="text-left pr-3">IFF</th>
                  <th className="text-left pr-3">ALT</th>
                  <th className="text-left pr-3">SPD</th>
                  <th className="text-left pr-3">STATUS</th>
                </tr>
              </thead>
              <tbody>
                {AIR_TRACKS.map((t) => (
                  <tr key={t.id} className={`border-b border-zinc-900/60 transition-colors ${iffRowBg(t.iff)}`}>
                    <td className={`py-1 pr-3 font-bold ${iffColor(t.iff)}`}>{t.callsign}</td>
                    <td className="pr-3 text-zinc-300">{t.type}</td>
                    <td className={`pr-3 ${iffColor(t.iff)}`}>{t.iff}</td>
                    <td className="pr-3 text-zinc-400">{t.alt}</td>
                    <td className="pr-3 text-zinc-400">{t.spd}</td>
                    <td className={`pr-3 ${t.iff === 'HOSTILE' ? 'text-red-400 font-bold' : 'text-zinc-400'}`}>{t.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Maritime track table */}
        <div className="video-feed-frame tac-card p-4 relative">
          <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
          <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
            <span className="text-[7px] text-emerald-500/60 font-bold tracking-[0.2em]">AIS LIVE</span>
          </div>
          <div className="tac-section-header mb-3 relative z-[1]">
            <Anchor size={14} className="text-emerald-400 drop-shadow-[0_0_6px_rgba(16,185,129,0.4)]" />
            <span className="glow-green">MARITIME (AIS) PICTURE</span>
            <span className="text-[9px] text-zinc-600 ml-2 normal-case tracking-normal font-normal">AIS / NAVCENT</span>
            <span className="ml-auto text-[9px] normal-case font-normal tracking-normal">
              <span className="text-cyan-400 font-bold">{MAR_TRACKS.filter(t => t.iff === 'FRIEND').length} FRIEND</span>
              <span className="text-zinc-600 mx-1">·</span>
              <span className="text-red-400 font-bold animate-pulse">{MAR_TRACKS.filter(t => t.iff === 'HOSTILE').length} HOSTILE</span>
              <span className="text-zinc-600 mx-1">·</span>
              <span className="text-amber-400 font-bold">{MAR_TRACKS.filter(t => t.iff === 'NEUTRAL').length} NEUTRAL</span>
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[10px] font-mono border-collapse">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 tracking-widest">
                  <th className="text-left py-1.5 pr-3">VESSEL</th>
                  <th className="text-left pr-3">CLASS</th>
                  <th className="text-left pr-3">IFF</th>
                  <th className="text-left pr-3">POS</th>
                  <th className="text-left pr-3">SOG</th>
                  <th className="text-left pr-3">STATUS</th>
                </tr>
              </thead>
              <tbody>
                {MAR_TRACKS.map((t) => (
                  <tr key={t.id} className={`border-b border-zinc-900/60 transition-colors ${iffRowBg(t.iff)}`}>
                    <td className={`py-1 pr-3 font-bold ${iffColor(t.iff)}`}>{t.name}</td>
                    <td className="pr-3 text-zinc-300">{t.type}</td>
                    <td className={`pr-3 ${iffColor(t.iff)}`}>{t.iff}</td>
                    <td className="pr-3 text-zinc-500 text-[9px]">{t.pos}</td>
                    <td className="pr-3 text-zinc-400">{t.sog}</td>
                    <td className={`pr-3 ${t.iff === 'HOSTILE' ? 'text-red-400 font-bold' : t.status.includes('DAMAGE') || t.status.includes('DEGRADED') ? 'text-amber-400' : 'text-zinc-400'}`}>{t.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ORACLE-9 live threat probabilities — cinematic */}
      <div className="tac-card tac-card-critical p-4 relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" style={{background: 'linear-gradient(135deg, rgba(239,68,68,0.03) 0%, transparent 50%)'}} />
        <div className="tac-section-header mb-3 relative z-[1]">
          <AlertTriangle size={14} className="text-red-400 drop-shadow-[0_0_6px_rgba(239,68,68,0.5)]" />
          <span className="glow-red">ORACLE-9 LIVE THREAT PROBABILITIES</span>
          <span className="ml-auto flex items-center gap-1.5 text-[8px] text-red-400/60 tracking-widest normal-case font-normal">
            <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
            BAYESIAN ENGINE ACTIVE
          </span>
        </div>
        <OraclePanel />
      </div>

      {/* Threat events — cinematic */}
      <div className="video-feed-frame tac-card p-4 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
          <span className="text-[7px] text-red-400/60 font-bold tracking-[0.2em]">THREAT FEED</span>
        </div>
        <div className="tac-section-header mb-3 relative z-[1]">
          <AlertTriangle size={14} className="text-red-400 drop-shadow-[0_0_6px_rgba(239,68,68,0.4)]" />
          <span className="glow-red">THREAT / CTF EVENTS</span>
          <span className="text-[9px] text-zinc-600 ml-2 normal-case tracking-normal font-normal">Most recent first</span>
          {liveEvents.length > 0 && (
            <span className="ml-auto flex items-center gap-1 text-[8px] text-emerald-500 tracking-widest">
              <Cpu size={8} />{liveEvents.length} LIVE
            </span>
          )}
        </div>
        <div className="space-y-2">
          {/* Live AI-extracted events first */}
          {liveEvents.map((ev) => (
            <div key={ev.event_id} className={`border rounded-sm px-3 py-2 text-[10px] font-mono flex gap-3 items-start ${
              ev.priority === 'CRITICAL' ? SEVERITY_STYLE['CRITICAL'] :
              ev.priority === 'HIGH'     ? SEVERITY_STYLE['HIGH'] :
              ev.priority === 'MEDIUM'   ? SEVERITY_STYLE['MEDIUM'] :
              SEVERITY_STYLE['INFO']
            } border-l-2 border-l-emerald-800`}>
              {ev.priority === 'CRITICAL' && (
                <span className="animate-pulse text-red-500 shrink-0 mt-0.5 text-xs leading-none">●</span>
              )}
              <div className="flex-shrink-0 text-zinc-500">{ev.time_zulu}</div>
              <div className="flex-shrink-0 font-bold w-16">{ev.type}</div>
              <div className="text-zinc-300 flex-1">{ev.body}</div>
              <div className="flex items-center gap-1">
                <div className="flex-shrink-0 font-bold">{ev.priority}</div>
                <Cpu size={7} className="text-emerald-700" />
              </div>
            </div>
          ))}
          {/* Live intel fallback when scenario_events is empty */}
          {liveEvents.length === 0 && intelFallback.map((item) => (
            <div key={item.id} className={`border rounded-sm px-3 py-2 text-[10px] font-mono flex gap-3 items-start ${
              item.confidence >= 85 ? SEVERITY_STYLE['CRITICAL'] :
              item.confidence >= 70 ? SEVERITY_STYLE['HIGH'] :
              item.confidence >= 60 ? SEVERITY_STYLE['MEDIUM'] :
              SEVERITY_STYLE['INFO']
            } border-l-2 border-l-cyan-900`}>
              <div className="flex-shrink-0 text-zinc-500">{new Date(item.created_at).toISOString().slice(11,16)}Z</div>
              <div className="flex-shrink-0 font-bold w-16 text-cyan-500">{item.theater || 'INTEL'}</div>
              <div className="text-zinc-300 flex-1">
                <span className="font-bold">{item.title}</span>
                {item.summary ? <span className="text-zinc-500"> — {item.summary}</span> : null}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <span className="text-[8px] text-zinc-600">CONF {item.confidence}%</span>
                {item.source_url && item.source_url !== '#' && (
                  <a href={item.source_url} target="_blank" rel="noopener noreferrer"
                     aria-label={`Source: ${item.source_name}`}
                     className="text-cyan-700 hover:text-cyan-400 transition-colors">
                    <ExternalLink size={7} />
                  </a>
                )}
              </div>
            </div>
          ))}
          {liveEvents.length === 0 && intelFallback.length === 0 && (
            <p className="text-[10px] text-zinc-600 text-center py-4 tracking-widest">AWAITING LIVE INTEL FEED</p>
          )}
        </div>
      </div>

      {/* Source attribution footer */}
      <div className="tac-card-intel p-4">
        <div className="tac-section-header mb-3">
          DATA SOURCES &amp; ATTRIBUTION
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {SOURCES.map((s) => (
            <div key={s.label} className="text-[9px] space-y-0.5">
              <div className="flex items-center gap-1 text-cyan-400/80 font-semibold">
                {s.label}
                {s.url !== '#' && (
                  <a href={s.url} target="_blank" rel="noopener noreferrer"
                     className="text-zinc-600 hover:text-cyan-400 transition-colors"
                     aria-label={`Open ${s.label}`}>
                    <ExternalLink size={8} />
                  </a>
                )}
              </div>
              <div className="text-zinc-600 leading-relaxed">{s.note}</div>
            </div>
          ))}
        </div>
        <div className="mt-3 pt-3 border-t border-zinc-800/60 text-[9px] text-zinc-700 leading-relaxed">
          <strong className="text-zinc-600">ABOUT THIS FEED:</strong> This Combined Operations Picture is an <strong>AI-synthesized live analysis</strong> built from{' '}
          open-source AIS, ADS-B, and OSINT reporting. AIS positions reflect publicly available vessel tracking. Air track data is AI-projected from open-source feeds.
          No classified material is represented. Geographic basemap references: OpenStreetMap contributors, CIA
          World Factbook (Persian Gulf). Historical figures and organisations cited for context only.
          Source attribution links lead to openly available reference sites.
        </div>
      </div>
    </div>
  )
}
