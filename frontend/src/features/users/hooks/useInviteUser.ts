import { useMutation, useQueryClient } from '@tanstack/react-query'
import { usersService } from '@/services/users.service'
import type { InviteUserPayload } from '../types'

export function useInviteUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: InviteUserPayload) => usersService.inviteUser(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users', 'list'] }),
  })
}
