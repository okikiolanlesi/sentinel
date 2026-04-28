export type UserRole = 'admin' | 'analyst' | 'viewer'

export interface AuthUser {
  id: string
  email: string
  firstName: string
  lastName: string
  role: UserRole
  organization: string
  isActive?: boolean
  createdAt?: string
  lastLogin?: string
  avatarUrl?: string
}

export interface AuthResponse {
  user: AuthUser
  token: string
}

export interface SignInPayload {
  email: string
  password: string
  rememberMe: boolean
}

export interface SignUpPayload {
  organizationName: string
  firstName: string
  lastName: string
  email: string
  password: string
}
