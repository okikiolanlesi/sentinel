import { useQuery } from '@tanstack/react-query'
import { scanService } from '@/services/scan.service'
import type { ScanHistoryParams } from '../types'

export function useScanHistory(params?: ScanHistoryParams) {
  return useQuery({
    queryKey: ['scan', 'history', params],
    queryFn: () => scanService.getHistory(params),
  })
}
