import { useQuery } from '@tanstack/react-query'
import { dashboardService } from '@/services/dashboard.service'

export function useAuditLog(params?: { page?: number; page_size?: number; action_filter?: string }) {
  return useQuery({
    queryKey: ['dashboard', 'audit-log', params],
    queryFn: () => dashboardService.getAuditLog(params),
  })
}
