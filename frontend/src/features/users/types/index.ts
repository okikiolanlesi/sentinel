import type { UserRole } from '@/features/auth/types'

export interface ApiUser {
  id: string
  email: string
  full_name: string
  organisation: string
  role: UserRole
  is_active: boolean
  created_at: string
  last_login?: string
}

export interface UsersListResponse {
  users: ApiUser[]
  total: number
}

export interface InviteUserPayload {
  email: string
  full_name: string
  organisation: string
  role: UserRole
}

export interface InviteUserResponse {
  message: string
  user: ApiUser
  temporary_credentials: {
    email: string
    temporary_password: string
    warning: string
  }
}

export interface UpdateProfilePayload {
  full_name?: string
  organisation?: string
}
