import { useMutation, useQueryClient } from '@tanstack/react-query'
import { voiceService } from '@/services/voice.service'

export function useAnalyseVoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => voiceService.analyse(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['voice', 'history'] }),
  })
}
