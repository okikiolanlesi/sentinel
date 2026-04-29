import { useMutation, useQueryClient } from '@tanstack/react-query'
import { usersService } from '@/services/users.service'

export function useActivateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => usersService.activate(userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users', 'list'] }),
  })
}
