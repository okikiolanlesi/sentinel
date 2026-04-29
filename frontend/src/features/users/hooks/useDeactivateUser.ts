import { useMutation, useQueryClient } from '@tanstack/react-query'
import { usersService } from '@/services/users.service'

export function useDeactivateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => usersService.deactivate(userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users', 'list'] }),
  })
}
