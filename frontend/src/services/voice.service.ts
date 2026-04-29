import { http } from '@/lib/http'
import type { VoiceAnalysis, VoiceHistoryResponse } from '@/features/deepfake/types'

export const voiceService = {
  analyse: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return http
      .post<VoiceAnalysis>('/api/voice/analyse', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  getHistory: (params?: { page?: number; page_size?: number }) =>
    http.get<VoiceHistoryResponse>('/api/voice/history', { params }).then((r) => r.data),

  getAnalysis: (analysisId: string) =>
    http.get<VoiceAnalysis>(`/api/voice/${analysisId}`).then((r) => r.data),
}
