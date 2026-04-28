import { useMutation, useQueryClient } from '@tanstack/react-query'
import { scanService } from '@/services/scan.service'
import type { ScanMessage } from '../types'

export function useScanMessage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: ScanMessage) => scanService.scanMessage(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scan', 'history'] })
      qc.invalidateQueries({ queryKey: ['dashboard', 'stats'] })
    },
  })
}
