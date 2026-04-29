import { useQuery } from '@tanstack/react-query'
import { scanService } from '@/services/scan.service'

export function useModelEvaluation() {
  return useQuery({
    queryKey: ['scan', 'evaluate'],
    queryFn: scanService.evaluate,
  })
}
