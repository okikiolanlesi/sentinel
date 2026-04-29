import type { ThreatLevel, MessageType, ScanAction } from '@/types'

export interface ScanResult {
  id: string
  risk_score: number
  threat_level: ThreatLevel
  flags: string[]
  action: ScanAction
  reasoning: string
  is_scam: boolean
  confirmed?: boolean
  created_at: string
}

export interface ScanMessage {
  content: string
  message_type: MessageType
  sender?: string
}

export interface BatchScanPayload {
  messages: ScanMessage[]
}

export interface BatchScanResult {
  total_scanned: number
  threats_found: number
  breakdown: Record<ThreatLevel, number>
  results: ScanResult[]
}

export interface ScanHistoryParams {
  threat_level?: ThreatLevel
  message_type?: MessageType
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

export interface ScanHistoryResponse {
  items: ScanResult[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface EvalResult {
  id: string
  preview: string
  expected: string
  predicted: string
  risk_score: number
  correct: boolean
}

export interface ModelEvalResponse {
  status: string
  accuracy_percent: number
  correct: number
  total: number
  results: EvalResult[]
}
