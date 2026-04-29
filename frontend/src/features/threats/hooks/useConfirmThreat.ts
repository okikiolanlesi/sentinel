import { useMutation, useQueryClient } from '@tanstack/react-query'
import { scanService } from '@/services/scan.service'

export function useConfirmThreat() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (scanId: string) => scanService.confirmThreat(scanId),
    onSuccess: (_, scanId) => {
      qc.invalidateQueries({ queryKey: ['scan', 'result', scanId] })
      qc.invalidateQueries({ queryKey: ['scan', 'history'] })
    },
  })
}
