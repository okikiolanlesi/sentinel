import { useQuery } from '@tanstack/react-query'
import { scanService } from '@/services/scan.service'

export function useScanResult(scanId: string) {
  return useQuery({
    queryKey: ['scan', 'result', scanId],
    queryFn: () => scanService.getResult(scanId),
    enabled: !!scanId,
  })
}
