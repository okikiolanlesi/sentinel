import { useQuery } from '@tanstack/react-query'
import { dashboardService } from '@/services/dashboard.service'

export function useTrends(days = 30) {
  return useQuery({
    queryKey: ['dashboard', 'trends', days],
    queryFn: () => dashboardService.getTrends(days),
  })
}
