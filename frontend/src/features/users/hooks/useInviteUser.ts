import { useMutation, useQueryClient } from '@tanstack/react-query'
import { usersService } from '@/services/users.service'
import type { InviteUserPayload } from '@/services/users.service'

export function useInviteUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: InviteUserPayload) => usersService.invite(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users', 'list'] }),
  })
}