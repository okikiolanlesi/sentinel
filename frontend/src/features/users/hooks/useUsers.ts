import { useQuery } from '@tanstack/react-query'
import { usersService } from '@/services/users.service'

export function useUsers(params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ['users', 'list', params],
    queryFn: () => usersService.listUsers(params),
  })
}
