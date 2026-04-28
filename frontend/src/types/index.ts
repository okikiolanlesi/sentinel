export type ThreatLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'CLEAN'
export type MessageType = 'sms' | 'whatsapp' | 'transcript'
export type ScanAction = 'BLOCK' | 'REVIEW' | 'ALLOW'

export interface ApiResponse<T> {
  data: T
  message: string
  success: boolean
}

export interface PaginatedResponse<T> {
  data: T[]
  message: string
  success: boolean
  total: number
  page: number
  limit: number
}
