/** ── Domain types shared across server and client ── */

export type AgentStatus = 'ON STATION' | 'ENGAGED' | 'MONITORING' | 'ALERT'
export type AgentDomain = 'ISR' | 'Cyber' | 'SIGINT' | 'OSINT' | 'Prediction' | 'Strike' | 'Maritime' | 'IMINT' | 'Fusion' | 'EW' | 'STRATCOM' | 'IO' | 'Analytics'
export type AgentPriority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'

export type SourceType = 'Official' | 'Wire' | 'Analysis' | 'Media' | 'OSINT' | 'SIGINT'

export type Theater =
  | 'Hormuz'
  | 'Gulf'
  | 'Cyber'
  | 'Air'
  | 'Land'
  | 'Diplomatic'
  | 'Nuclear'
  | 'Maritime'
  | 'Economic'

/** Intel report row (mirrors the Supabase `intel` table) */
export interface Intel {
  id: string
  title: string
  summary: string
  theater: string           // Theater enum above
  confidence: number        // 0-100
  source_url: string | null // Primary citation URL
  source_name: string | null // e.g. "Reuters", "CENTCOM", "ISW"
  source_type: string | null // SourceType enum above
  verified: boolean         // Editorially confirmed / cross-sourced
  tags: string[] | null     // e.g. ["missile","naval","drone"]
  author: string | null     // Analyst or byline
  created_at: string        // ISO timestamp
}

/** AI Agent — currently static; extend to Supabase-backed in a future sprint */
export interface Agent {
  id: string
  name: string
  role: string
  domain: AgentDomain
  status: AgentStatus
  priority: AgentPriority
  confidence: number        // 0-100 — signal/assessment confidence
  tasking: string           // Current mission tasking order
  threat_focus: string      // Specific entity / system / area being tracked
  quote: string             // Latest high-priority reasoning excerpt
  lastUpdate: string        // Human-readable time string, e.g. "02:14 UTC"
  actions: {                // Timestamped activity log (most recent first)
    time: string
    entry: string
  }[]
}

/** News source entry for the Source Directory page */
export interface NewsSource {
  id: string
  name: string
  shortName: string
  category: 'Wire' | 'Broadcast' | 'Official' | 'Analysis' | 'Specialized' | 'OSINT' | 'Homeland'
  description: string
  url: string
  rssUrl?: string
  region?: string        // Coverage focus
  reliability: 'High' | 'Medium' | 'Variable'
}

/** Supabase DB helper types */
export type Database = {
  public: {
    Tables: {
      intel: {
        Row: Intel
        Insert: Omit<Intel, 'id' | 'created_at'>
        Update: Partial<Omit<Intel, 'id'>>
        Relationships: []
      }
      newsroom_scripts: {
        Row: {
          conflict_day:  number
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          segments_json: any
          model:         string
          created_at:    string
        }
        Insert: {
          conflict_day:  number
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          segments_json: any
          model?:        string
        }
        Update: {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          segments_json?: any
          model?:         string
        }
        Relationships: []
      }
      model_snapshots: {
        Row: {
          id:             string
          conflict_day:   number
          oracle_payload: string | null
          compass_payload: string | null
          herald_summary: string | null
          created_at:     string
        }
        Insert: {
          conflict_day:    number
          oracle_payload?: string | null
          compass_payload?: string | null
          herald_summary?:  string | null
        }
        Update: {
          conflict_day?:    number
          oracle_payload?:  string | null
          compass_payload?: string | null
          herald_summary?:  string | null
        }
        Relationships: []
      }
    }
  }
}
