import { http } from '@/lib/http'
import type {
  ApiUser,
  UsersListResponse,
  InviteUserPayload,
  InviteUserResponse,
  UpdateProfilePayload,
} from '@/features/users/types'
import type { UserRole } from '@/features/auth/types'

export const usersService = {
  listUsers: (params?: { page?: number; page_size?: number }) =>
    http.get<UsersListResponse>('/api/users', { params }).then((r) => r.data),

  inviteUser: (payload: InviteUserPayload) =>
    http.post<InviteUserResponse>('/api/users/invite', payload).then((r) => r.data),

  changeRole: (userId: string, newRole: UserRole) =>
    http.put<ApiUser>(`/api/users/${userId}/role`, null, { params: { new_role: newRole } }).then((r) => r.data),

  deactivate: (userId: string) =>
    http.put<ApiUser>(`/api/users/${userId}/deactivate`).then((r) => r.data),

  activate: (userId: string) =>
    http.put<ApiUser>(`/api/users/${userId}/activate`).then((r) => r.data),

  deleteUser: (userId: string) =>
    http.delete<{ message: string; user_id: string }>(`/api/users/${userId}`).then((r) => r.data),

  getProfile: () =>
    http.get<ApiUser>('/api/users/me').then((r) => r.data),

  updateProfile: (payload: UpdateProfilePayload) =>
    http.put<ApiUser>('/api/users/me', payload).then((r) => r.data),
}
