// Re-export everything from scan.service for backwards compatibility with sentinel-main hooks
export type {
  ScanResult,
  ScanMessage,
  ScanRequestPayload,
  BatchScanPayload,
  BatchScanResult,
  ScanHistoryParams,
  ScanHistoryResponse,
  ModelEvalResponse,
  EvalResult,
  ThreatLevel,
  MessageType,
  ScanAction,
  ThreatStatus,
} from '@/services/scan.service'