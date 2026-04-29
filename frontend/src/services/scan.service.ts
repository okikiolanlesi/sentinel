import { http } from '@/lib/http'
import type {
  ScanResult,
  ScanMessage,
  BatchScanPayload,
  BatchScanResult,
  ScanHistoryParams,
  ScanHistoryResponse,
  ModelEvalResponse,
} from '@/features/threats/types'

export const scanService = {
  scanMessage: (payload: ScanMessage) =>
    http.post<ScanResult>('/api/scan/message', payload).then((r) => r.data),

  batchScan: (payload: BatchScanPayload) =>
    http.post<BatchScanResult>('/api/scan/batch', payload).then((r) => r.data),

  getHistory: (params?: ScanHistoryParams) =>
    http.get<ScanHistoryResponse>('/api/scan/history', { params }).then((r) => r.data),

  getResult: (scanId: string) =>
    http.get<ScanResult>(`/api/scan/${scanId}`).then((r) => r.data),

  confirmThreat: (scanId: string) =>
    http.post<ScanResult>(`/api/scan/${scanId}/confirm`).then((r) => r.data),

  evaluate: () =>
    http.get<ModelEvalResponse>('/api/scan/evaluate').then((r) => r.data),
}
