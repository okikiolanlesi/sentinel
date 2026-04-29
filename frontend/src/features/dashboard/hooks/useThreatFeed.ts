import { useQuery } from '@tanstack/react-query'
import { dashboardService } from '@/services/dashboard.service'

export function useThreatFeed(limit = 20) {
  return useQuery({
    queryKey: ['dashboard', 'threat-feed', limit],
    queryFn: () => dashboardService.getThreatFeed(limit),
    refetchInterval: 30_000,
  })
}
