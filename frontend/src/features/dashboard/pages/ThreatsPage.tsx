import { useState } from 'react'
import {
  ShieldAlert, Send, ChevronDown, ChevronUp, AlertCircle, CheckCircle2,
  Filter, Layers,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Select } from '@/components/ui/select'
import { Dialog } from '@/components/ui/dialog'
import { useScanMessage } from '@/features/threats/hooks/useScanMessage'
import { useScanHistory } from '@/features/threats/hooks/useScanHistory'
import { useConfirmThreat } from '@/features/threats/hooks/useConfirmThreat'
import { getApiErrorMessage } from '@/lib/errors'
import type { ScanResult, ScanHistoryParams } from '@/features/threats/types'
import type { ThreatLevel, MessageType } from '@/types'

const messageTypeOptions = [
  { value: 'sms',        label: 'SMS' },
  { value: 'whatsapp',   label: 'WhatsApp' },
  { value: 'transcript', label: 'Transcript' },
]
const threatLevelOptions = [
  { value: 'HIGH',   label: 'High' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'LOW',    label: 'Low' },
  { value: 'CLEAN',  label: 'Clean' },
]

function RiskBar({ score }: { score: number }) {
  const color =
    score >= 80 ? 'bg-red-500' :
    score >= 50 ? 'bg-orange-500' :
    score >= 20 ? 'bg-yellow-500' : 'bg-emerald-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs text-slate-400 font-mono w-8 text-right">{score.toFixed(0)}</span>
    </div>
  )
}

function ResultDetail({ result, onClose }: { result: ScanResult; onClose: () => void }) {
  const { mutate: confirm, isPending } = useConfirmThreat()

  return (
    <Dialog open onClose={onClose} title="Scan result detail" className="max-w-lg">
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Badge threat={result.threat_level}>{result.threat_level}</Badge>
          <span className="text-xs text-slate-500 font-mono">Risk: {result.risk_score.toFixed(1)}</span>
          <span className={`text-xs font-semibold ${result.action === 'BLOCK' ? 'text-red-400' : result.action === 'REVIEW' ? 'text-amber-400' : 'text-emerald-400'}`}>
            {result.action}
          </span>
          {result.confirmed && <Badge className="bg-emerald-500/12 text-emerald-400 border-emerald-500/25">Confirmed</Badge>}
        </div>

        <div>
          <p className="text-[11px] text-slate-500 mb-1.5 font-medium uppercase tracking-wide">Reasoning</p>
          <p className="text-sm text-slate-300 leading-relaxed bg-slate-800/60 rounded-lg p-3">{result.reasoning}</p>
        </div>

        {result.flags.length > 0 && (
          <div>
            <p className="text-[11px] text-slate-500 mb-1.5 font-medium uppercase tracking-wide">Flags</p>
            <div className="flex flex-wrap gap-1.5">
              {result.flags.map((f) => (
                <span key={f} className="px-2 py-0.5 bg-slate-800 border border-slate-700 rounded text-xs text-slate-400 font-mono">{f}</span>
              ))}
            </div>
          </div>
        )}

        <p className="text-[11px] text-slate-600">{new Date(result.created_at).toLocaleString()}</p>

        {!result.confirmed && (
          <Button
            onClick={() => confirm(result.id, { onSuccess: onClose })}
            disabled={isPending}
            className="w-full bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/25 h-9 text-sm"
          >
            {isPending ? 'Confirming…' : 'Confirm threat'}
          </Button>
        )}
      </div>
    </Dialog>
  )
}

export default function ThreatsPage() {
  const [content, setContent]       = useState('')
  const [msgType, setMsgType]       = useState<MessageType>('sms')
  const [sender, setSender]         = useState('')
  const [selected, setSelected]     = useState<ScanResult | null>(null)
  const [filters, setFilters]       = useState<ScanHistoryParams>({ page: 1, page_size: 20 })
  const [showFilters, setShowFilters] = useState(false)

  const { mutate: scan, isPending: scanning, data: scanResult, error: scanError, reset: resetScan } = useScanMessage()
  const { data: history, isLoading: historyLoading } = useScanHistory(filters)
  const { mutate: confirm } = useConfirmThreat()

  function handleScan() {
    if (!content.trim()) return
    resetScan()
    scan({ content, message_type: msgType, sender: sender || undefined })
  }

  return (
    <div className="space-y-7">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-slate-800 border border-slate-700">
          <ShieldAlert className="size-4 text-slate-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Threats</h1>
          <p className="text-slate-500 text-xs mt-0.5">Scan messages and review detected threats.</p>
        </div>
      </div>

      {/* Scan panel */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <p className="text-sm font-medium text-slate-300">Scan a message</p>

        <Textarea
          rows={4}
          placeholder="Paste the message content here…"
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />

        <div className="flex gap-3">
          <Select
            options={messageTypeOptions}
            value={msgType}
            onChange={(e) => setMsgType(e.target.value as MessageType)}
            className="w-36"
          />
          <input
            type="text"
            placeholder="Sender (optional)"
            value={sender}
            onChange={(e) => setSender(e.target.value)}
            className="flex-1 bg-slate-900 border border-slate-700 text-white text-sm placeholder-slate-600 rounded-lg px-3 h-10 focus:outline-none focus:border-blue-500/60 focus:ring-2 focus:ring-blue-500/20"
          />
          <Button
            onClick={handleScan}
            disabled={scanning || !content.trim()}
            className="bg-blue-600 hover:bg-blue-500 text-white border-0 h-10 px-5 text-sm font-medium disabled:opacity-60 shrink-0"
          >
            {scanning ? (
              <span className="flex items-center gap-2">
                <span className="size-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                Scanning…
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                <Send className="size-3.5" /> Scan
              </span>
            )}
          </Button>
        </div>

        {scanError && (
          <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-red-500/8 border border-red-500/20 text-sm text-red-400">
            <AlertCircle className="size-4 shrink-0 mt-0.5" />
            {getApiErrorMessage(scanError)}
          </div>
        )}

        {scanResult && (
          <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-3">
            <div className="flex items-center gap-3">
              <Badge threat={scanResult.threat_level}>{scanResult.threat_level}</Badge>
              <span className={`text-sm font-bold ${scanResult.action === 'BLOCK' ? 'text-red-400' : scanResult.action === 'REVIEW' ? 'text-amber-400' : 'text-emerald-400'}`}>
                {scanResult.action}
              </span>
              <span className="text-xs text-slate-500 ml-auto">Risk: {scanResult.risk_score.toFixed(1)}/100</span>
            </div>
            <RiskBar score={scanResult.risk_score} />
            <p className="text-sm text-slate-300 leading-relaxed">{scanResult.reasoning}</p>
            {scanResult.flags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {scanResult.flags.map((f) => (
                  <span key={f} className="px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-400 font-mono">{f}</span>
                ))}
              </div>
            )}
            <div className="flex items-center justify-between pt-1">
              <span className={`text-xs font-medium ${scanResult.is_scam ? 'text-red-400' : 'text-emerald-400'}`}>
                {scanResult.is_scam ? '⚠ Classified as scam' : '✓ Not a scam'}
              </span>
              {!scanResult.confirmed && (
                <button
                  onClick={() => confirm(scanResult.id)}
                  className="text-xs text-slate-500 hover:text-emerald-400 transition-colors flex items-center gap-1"
                >
                  <CheckCircle2 className="size-3.5" /> Confirm
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* History */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Layers className="size-4 text-slate-500" />
            <p className="text-sm font-medium text-slate-300">Scan history</p>
            {history && <span className="text-xs text-slate-600">({history.total})</span>}
          </div>
          <button
            onClick={() => setShowFilters((p) => !p)}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            <Filter className="size-3.5" />
            Filters
            {showFilters ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
          </button>
        </div>

        {showFilters && (
          <div className="px-5 py-3.5 border-b border-slate-800 bg-slate-800/30 flex flex-wrap gap-3">
            <Select
              placeholder="All levels"
              options={threatLevelOptions}
              value={filters.threat_level ?? ''}
              onChange={(e) => setFilters((p) => ({ ...p, threat_level: (e.target.value as ThreatLevel) || undefined, page: 1 }))}
              className="w-36"
            />
            <Select
              placeholder="All types"
              options={messageTypeOptions}
              value={filters.message_type ?? ''}
              onChange={(e) => setFilters((p) => ({ ...p, message_type: (e.target.value as MessageType) || undefined, page: 1 }))}
              className="w-36"
            />
            <input
              type="date"
              value={filters.start_date ?? ''}
              onChange={(e) => setFilters((p) => ({ ...p, start_date: e.target.value || undefined, page: 1 }))}
              className="bg-slate-900 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 h-10 focus:outline-none focus:border-blue-500/60 focus:ring-2 focus:ring-blue-500/20"
            />
            <input
              type="date"
              value={filters.end_date ?? ''}
              onChange={(e) => setFilters((p) => ({ ...p, end_date: e.target.value || undefined, page: 1 }))}
              className="bg-slate-900 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 h-10 focus:outline-none focus:border-blue-500/60 focus:ring-2 focus:ring-blue-500/20"
            />
            <button
              onClick={() => setFilters({ page: 1, page_size: 20 })}
              className="text-xs text-slate-500 hover:text-slate-300 px-3 h-10 rounded-lg border border-slate-700 hover:border-slate-600 transition-colors"
            >
              Clear
            </button>
          </div>
        )}

        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-800">
              <th className="text-left px-5 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Preview</th>
              <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wide hidden sm:table-cell">Type</th>
              <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Level</th>
              <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell w-40">Risk</th>
              <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Action</th>
              <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">Date</th>
            </tr>
          </thead>
          <tbody>
            {historyLoading && (
              <tr><td colSpan={6} className="px-5 py-10 text-center"><span className="inline-block size-5 rounded-full border-2 border-slate-700 border-t-blue-400 animate-spin" /></td></tr>
            )}
            {!historyLoading && history?.items.length === 0 && (
              <tr><td colSpan={6} className="px-5 py-10 text-center text-slate-500 text-sm">No results found.</td></tr>
            )}
            {history?.items.map((item) => (
              <tr
                key={item.id}
                className="border-b border-slate-800/60 last:border-0 hover:bg-slate-800/20 cursor-pointer transition-colors"
                onClick={() => setSelected(item)}
              >
                <td className="px-5 py-3.5 text-sm text-slate-300 max-w-xs">
                  <p className="truncate">{item.reasoning?.slice(0, 60) || '—'}</p>
                </td>
                <td className="px-4 py-3.5 hidden sm:table-cell">
                  <span className="text-xs font-medium text-slate-500 uppercase">{(item as unknown as { message_type?: string }).message_type ?? '—'}</span>
                </td>
                <td className="px-4 py-3.5"><Badge threat={item.threat_level}>{item.threat_level}</Badge></td>
                <td className="px-4 py-3.5 hidden md:table-cell w-40"><RiskBar score={item.risk_score} /></td>
                <td className="px-4 py-3.5">
                  <span className={`text-xs font-semibold ${item.action === 'BLOCK' ? 'text-red-400' : item.action === 'REVIEW' ? 'text-amber-400' : 'text-emerald-400'}`}>
                    {item.action}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-xs text-slate-500 hidden lg:table-cell">
                  {new Date(item.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {history && history.pages > 1 && (
          <div className="flex items-center justify-between px-5 py-3.5 border-t border-slate-800">
            <span className="text-xs text-slate-500">Page {history.page} of {history.pages}</span>
            <div className="flex gap-2">
              <button
                disabled={history.page <= 1}
                onClick={() => setFilters((p) => ({ ...p, page: (p.page ?? 1) - 1 }))}
                className="px-3 h-7 text-xs rounded-md border border-slate-700 text-slate-400 hover:text-white hover:border-slate-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <button
                disabled={history.page >= history.pages}
                onClick={() => setFilters((p) => ({ ...p, page: (p.page ?? 1) + 1 }))}
                className="px-3 h-7 text-xs rounded-md border border-slate-700 text-slate-400 hover:text-white hover:border-slate-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {selected && <ResultDetail result={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
