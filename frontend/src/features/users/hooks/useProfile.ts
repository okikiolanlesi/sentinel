import { useQuery } from '@tanstack/react-query'
import { usersService } from '@/services/users.service'

export function useProfile() {
  return useQuery({
    queryKey: ['users', 'profile'],
    queryFn: usersService.getProfile,
  })
}
