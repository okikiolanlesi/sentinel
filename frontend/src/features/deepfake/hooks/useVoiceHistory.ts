import { useQuery } from '@tanstack/react-query'
import { voiceService } from '@/services/voice.service'

export function useVoiceHistory(params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ['voice', 'history', params],
    queryFn: () => voiceService.getHistory(params),
  })
}
