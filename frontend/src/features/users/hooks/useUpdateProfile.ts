import { useMutation, useQueryClient } from '@tanstack/react-query'
import { usersService } from '@/services/users.service'
import type { UpdateProfilePayload } from '../types'

export function useUpdateProfile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: UpdateProfilePayload) => usersService.updateProfile(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users', 'profile'] })
      qc.invalidateQueries({ queryKey: ['users', 'list'] })
    },
  })
}
