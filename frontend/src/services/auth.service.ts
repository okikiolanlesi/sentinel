import { http } from '@/lib/http'
import type { AuthResponse, AuthUser, SignInPayload, SignUpPayload, UserRole } from '@/features/auth/types'

interface ApiUserData {
  id: string
  email: string
  full_name: string
  organisation: string
  role: UserRole
  is_active: boolean
  created_at?: string
  last_login?: string
}

interface ApiAuthResponse {
  access_token: string
  token_type: string
  user: ApiUserData
}

export interface ApiKeyResponse {
  message: string
  api_key: string
  warning: string
}

function mapApiUser(u: ApiUserData): AuthUser {
  const spaceIdx = u.full_name?.indexOf(' ') ?? -1
  const firstName = spaceIdx === -1 ? (u.full_name ?? '') : u.full_name.slice(0, spaceIdx)
  const lastName = spaceIdx === -1 ? '' : u.full_name.slice(spaceIdx + 1)
  return {
    id: u.id,
    email: u.email,
    firstName,
    lastName,
    role: u.role,
    organization: u.organisation,
    isActive: u.is_active,
    createdAt: u.created_at,
    lastLogin: u.last_login,
  }
}

export const authService = {
  async signIn(payload: SignInPayload): Promise<AuthResponse> {
    const { data } = await http.post<ApiAuthResponse>('/api/auth/login', {
      email: payload.email,
      password: payload.password,
    })
    return { user: mapApiUser(data.user), token: data.access_token }
  },

  async signUp(payload: SignUpPayload): Promise<AuthResponse> {
    const { data } = await http.post<ApiAuthResponse>('/api/auth/register', {
      email: payload.email,
      password: payload.password,
      full_name: `${payload.firstName} ${payload.lastName}`.trim(),
      organisation: payload.organizationName,
    })
    return { user: mapApiUser(data.user), token: data.access_token }
  },

  async getCurrentUser(): Promise<AuthUser> {
    const { data } = await http.get<ApiUserData>('/api/auth/me')
    return mapApiUser(data)
  },

  async generateApiKey(): Promise<ApiKeyResponse> {
    const { data } = await http.post<ApiKeyResponse>('/api/auth/generate-key')
    return data
  },
}
