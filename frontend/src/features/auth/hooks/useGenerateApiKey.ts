import { useMutation } from '@tanstack/react-query'
import { authService } from '@/services/auth.service'

export function useGenerateApiKey() {
  return useMutation({
    mutationFn: authService.generateApiKey,
  })
}
