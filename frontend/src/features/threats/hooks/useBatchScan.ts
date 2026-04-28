import { useMutation, useQueryClient } from '@tanstack/react-query'
import { scanService } from '@/services/scan.service'
import type { BatchScanPayload } from '../types'

export function useBatchScan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: BatchScanPayload) => scanService.batchScan(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scan', 'history'] })
      qc.invalidateQueries({ queryKey: ['dashboard', 'stats'] })
    },
  })
}
