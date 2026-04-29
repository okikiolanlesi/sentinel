import { useQuery } from '@tanstack/react-query'
import { voiceService } from '@/services/voice.service'

export function useVoiceAnalysis(analysisId: string) {
  return useQuery({
    queryKey: ['voice', 'analysis', analysisId],
    queryFn: () => voiceService.getAnalysis(analysisId),
    enabled: !!analysisId,
  })
}
