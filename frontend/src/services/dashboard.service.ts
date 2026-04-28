import { http } from '@/lib/http'
import type {
  DashboardStats,
  ThreatFeedResponse,
  TrendsResponse,
  AuditLogResponse,
} from '@/features/dashboard/types'

export const dashboardService = {
  getStats: () =>
    http.get<DashboardStats>('/api/dashboard/stats').then((r) => r.data),

  getThreatFeed: (limit = 20) =>
    http.get<ThreatFeedResponse>('/api/dashboard/threat-feed', { params: { limit } }).then((r) => r.data),

  getTrends: (days = 30) =>
    http.get<TrendsResponse>('/api/dashboard/trends', { params: { days } }).then((r) => r.data),

  getAuditLog: (params?: { page?: number; page_size?: number; action_filter?: string }) =>
    http.get<AuditLogResponse>('/api/dashboard/audit-log', { params }).then((r) => r.data),
}
