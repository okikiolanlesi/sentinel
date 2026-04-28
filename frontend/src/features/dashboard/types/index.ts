import type { ThreatLevel, MessageType } from '@/types'

export interface DashboardStats {
  total_scanned: number
  threats_detected: number
  deepfakes_found: number
  avg_risk_score: number
  blocked_today: number
  active_campaigns: number
  breakdown: Record<ThreatLevel, number>
}

export interface ThreatFeedItem {
  id: string
  content_preview: string
  risk_score: number
  threat_level: ThreatLevel
  message_type: MessageType
  sender: string
  created_at: string
}

export interface ThreatFeedResponse {
  items: ThreatFeedItem[]
}

export interface TrendPoint {
  date: string
  total_scanned: number
  threats_detected: number
}

export interface TrendsResponse {
  trends: TrendPoint[]
}

export interface AuditLogItem {
  id: string
  user_id: string
  action: string
  resource: string
  details: string
  ip_address: string
  created_at: string
}

export interface AuditLogResponse {
  items: AuditLogItem[]
  total: number
  page: number
  page_size: number
  pages: number
}
