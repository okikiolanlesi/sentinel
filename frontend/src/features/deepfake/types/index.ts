import type { ThreatLevel } from '@/types'

export interface VoiceAnalysis {
  id: string
  transcript: string
  deepfake_probability: number
  risk_score: number
  threat_level: ThreatLevel
  flags: string[]
  reasoning: string
  is_scam: boolean
  created_at: string
}

export interface VoiceHistoryItem {
  id: string
  transcript_preview: string
  deepfake_probability: number
  risk_score: number
  threat_level: ThreatLevel
  created_at: string
}

export interface VoiceHistoryResponse {
  items: VoiceHistoryItem[]
  total: number
  page: number
  page_size: number
  pages: number
}
