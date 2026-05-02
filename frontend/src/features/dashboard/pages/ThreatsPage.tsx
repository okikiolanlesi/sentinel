import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Loader2, AlertCircle, Send, ShieldAlert, ChevronDown, ChevronUp,
  ArrowUpCircle, PenLine, Layers, RefreshCw,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { RiskBadge, ScoreBar } from '@/components/RiskBadge'
import {
  scanService,
  type MessageType, type ScanResult, type ThreatLevel,
  type ThreatStatus, type ScanAction,
} from '@/services/scan.service'
import { getApiErrorMessage } from '@/lib/errors'
import { formatRelativeTime } from '@/lib/format'
import { useAuthStore } from '@/store/auth.store'

const MESSAGE_TYPES: { value: MessageType; label: string }[] = [
  { value: 'sms', label: 'SMS' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'transcript', label: 'Call transcript' },
]

const THREAT_FILTERS: { value: ThreatLevel | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All' },
  { value: 'HIGH', label: 'High' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'LOW', label: 'Low' },
  { value: 'CLEAN', label: 'Clean' },
]

const STATUS_COLORS: Record<ThreatStatus, string> = {
  new: 'bg-slate-700 text-slate-300',
  reviewing: 'bg-blue-500/20 text-blue-400',
  escalated: 'bg-red-500/20 text-red-400',
  resolved: 'bg-emerald-500/20 text-emerald-400',
  closed: 'bg-slate-600/40 text-slate-500',
}

const NEXT_STATUSES: Record<ThreatStatus, ThreatStatus[]> = {
  new: ['reviewing', 'escalated'],
  reviewing: ['escalated', 'resolved', 'closed'],
  escalated: ['reviewing', 'resolved', 'closed'],
  resolved: ['closed'],
  closed: [],
}

function StatusBadge({
  status,
  scanId,
  onUpdate,
}: {
  status: ThreatStatus
  scanId: string
  onUpdate: (scanId: string, newStatus: ThreatStatus) => void
}) {
  const [open, setOpen] = useState(false)
  const nexts = NEXT_STATUSES[status]

  return (
    <div className="relative inline-block">
      <button
        onClick={() => nexts.length > 0 && setOpen((p) => !p)}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold uppercase ${STATUS_COLORS[status]}`}
        title={nexts.length === 0 ? 'Terminal state' : 'Change status'}
      >
        {status}
        {nexts.length > 0 && <ChevronDown className="size-3" />}
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-1 z-20 bg-slate-800 border border-slate-700 rounded-lg shadow-lg overflow-hidden min-w-[120px]">
          {nexts.map((s) => (
            <button
              key={s}
              onClick={() => { setOpen(false); onUpdate(scanId, s) }}
              className="w-full text-left px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700 transition-colors capitalize"
            >
              → {s}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function SuggestedActions({ actions }: { actions: string[] }) {
  const [expanded, setExpanded] = useState(false)
  if (!actions || actions.length === 0) return null
  return (
    <div className="mt-3">
      <button
        onClick={() => setExpanded((p) => !p)}
        className="flex items-center gap-1.5 text-xs text-amber-400 hover:text-amber-300 font-medium"
      >
        {expanded ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
        {actions.length} suggested action{actions.length > 1 ? 's' : ''}
      </button>
      {expanded && (
        <ul className="mt-2 space-y-1">
          {actions.map((a, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
              <span className="shrink-0 mt-0.5 text-amber-500">→</span>
              {a}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function EscalateModal({
  scanId,
  onClose,
  onDone,
}: {
  scanId: string
  onClose: () => void
  onDone: () => void
}) {
  const [reason, setReason] = useState('')
  const escalate = useMutation({
    mutationFn: () => scanService.escalateScan(scanId, { reason }),
    onSuccess: () => { onDone(); onClose() },
  })
  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 w-full max-w-md">
        <h3 className="text-sm font-bold text-white mb-4">Escalate threat</h3>
        <label className="text-xs text-slate-400 block mb-1.5">Reason (required)</label>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          className="w-full bg-slate-950 border border-slate-700 rounded-md px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-red-500/60 resize-none mb-4"
          placeholder="Describe why this needs escalation…"
        />
        {escalate.error && (
          <p className="text-xs text-red-400 mb-3">{getApiErrorMessage(escalate.error)}</p>
        )}
        <div className="flex gap-2 justify-end">
          <Button variant="ghost" size="sm" onClick={onClose} className="text-slate-400">Cancel</Button>
          <Button
            size="sm"
            disabled={reason.trim().length < 5 || escalate.isPending}
            onClick={() => escalate.mutate()}
            className="bg-red-600 hover:bg-red-500 text-white border-0"
          >
            {escalate.isPending ? <Loader2 className="size-3 animate-spin" /> : 'Escalate'}
          </Button>
        </div>
      </div>
    </div>
  )
}

function CorrectModal({
  scanId,
  onClose,
  onDone,
}: {
  scanId: string
  onClose: () => void
  onDone: () => void
}) {
  const [verdict, setVerdict] = useState<'SAFE' | 'SCAM'>('SAFE')
  const [correctedAction, setCorrectedAction] = useState<ScanAction>('ALLOW')
  const [reason, setReason] = useState('')

  const correct = useMutation({
    mutationFn: () =>
      scanService.correctScan(scanId, {
        corrected_verdict: verdict,
        corrected_action: correctedAction,
        correction_reason: reason,
      }),
    onSuccess: () => { onDone(); onClose() },
  })

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 w-full max-w-md">
        <h3 className="text-sm font-bold text-white mb-4">Mark as incorrect</h3>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="text-xs text-slate-400 block mb-1.5">Corrected verdict</label>
            <select
              value={verdict}
              onChange={(e) => setVerdict(e.target.value as 'SAFE' | 'SCAM')}
              className="w-full h-9 bg-slate-950 border border-slate-700 rounded-md px-3 text-sm text-white focus:outline-none focus:border-blue-500/60"
            >
              <option value="SAFE">SAFE</option>
              <option value="SCAM">SCAM</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1.5">Corrected action</label>
            <select
              value={correctedAction}
              onChange={(e) => setCorrectedAction(e.target.value as ScanAction)}
              className="w-full h-9 bg-slate-950 border border-slate-700 rounded-md px-3 text-sm text-white focus:outline-none focus:border-blue-500/60"
            >
              <option value="ALLOW">ALLOW</option>
              <option value="REVIEW">REVIEW</option>
              <option value="BLOCK">BLOCK</option>
            </select>
          </div>
        </div>
        <label className="text-xs text-slate-400 block mb-1.5">Reason (optional)</label>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={2}
          className="w-full bg-slate-950 border border-slate-700 rounded-md px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/60 resize-none mb-4"
          placeholder="Why was the AI wrong?"
        />
        {correct.error && (
          <p className="text-xs text-red-400 mb-3">{getApiErrorMessage(correct.error)}</p>
        )}
        <div className="flex gap-2 justify-end">
          <Button variant="ghost" size="sm" onClick={onClose} className="text-slate-400">Cancel</Button>
          <Button
            size="sm"
            disabled={correct.isPending}
            onClick={() => correct.mutate()}
            className="bg-amber-600 hover:bg-amber-500 text-white border-0"
          >
            {correct.isPending ? <Loader2 className="size-3 animate-spin" /> : 'Submit correction'}
          </Button>
        </div>
      </div>
    </div>
  )
}

function ScanResultCard({
  result,
  onStatusUpdate,
  onRefresh,
}: {
  result: ScanResult
  onStatusUpdate: (scanId: string, newStatus: ThreatStatus) => void
  onRefresh: () => void
}) {
  const [showEscalate, setShowEscalate] = useState(false)
  const [showCorrect, setShowCorrect] = useState(false)

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <RiskBadge level={result.threat_level} />
          <span className="text-xs font-mono text-slate-500">action: {result.action}</span>
          <StatusBadge
            status={(result.threat_status as ThreatStatus) || 'new'}
            scanId={result.id}
            onUpdate={onStatusUpdate}
          />
        </div>
        <div className="flex items-center gap-2">
          <ScoreBar score={result.risk_score} />
          {result.threat_status !== 'escalated' && result.threat_status !== 'closed' && (
            <button
              onClick={() => setShowEscalate(true)}
              className="flex items-center gap-1 px-2 py-1 text-[11px] text-red-400 border border-red-500/20 rounded-md hover:bg-red-500/10 transition-colors"
            >
              <ArrowUpCircle className="size-3" />
              Escalate
            </button>
          )}
          <button
            onClick={() => setShowCorrect(true)}
            className="flex items-center gap-1 px-2 py-1 text-[11px] text-amber-400 border border-amber-500/20 rounded-md hover:bg-amber-500/10 transition-colors"
          >
            <PenLine className="size-3" />
            Correct
          </button>
        </div>
      </div>

      {result.flags.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1.5">
          {result.flags.map((flag) => (
            <span key={flag} className="text-[11px] px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
              {flag}
            </span>
          ))}
        </div>
      )}

      <p className="text-sm text-slate-300 leading-relaxed">{result.reasoning}</p>
      <SuggestedActions actions={result.suggested_actions || []} />

      {showEscalate && (
        <EscalateModal scanId={result.id} onClose={() => setShowEscalate(false)} onDone={onRefresh} />
      )}
      {showCorrect && (
        <CorrectModal scanId={result.id} onClose={() => setShowCorrect(false)} onDone={onRefresh} />
      )}
    </div>
  )
}

type TabKey = 'scan' | 'escalations'

export default function ThreatsPage() {
  const qc = useQueryClient()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin'

  const [tab, setTab] = useState<TabKey>('scan')
  const [content, setContent] = useState('')
  const [messageType, setMessageType] = useState<MessageType>('sms')
  const [sender, setSender] = useState('')
  const [threatFilter, setThreatFilter] = useState<ThreatLevel | 'ALL'>('ALL')
  const [statusFilter, setStatusFilter] = useState<ThreatStatus | 'ALL'>('ALL')
  const [latestResult, setLatestResult] = useState<ScanResult | null>(null)

  const history = useQuery({
    queryKey: ['scan', 'history', threatFilter, statusFilter],
    queryFn: () =>
      scanService.getHistory({
        threat_level: threatFilter === 'ALL' ? null : threatFilter,
        threat_status: statusFilter === 'ALL' ? null : statusFilter,
        page_size: 30,
      }),
  })

  const escalations = useQuery({
    queryKey: ['scan', 'escalations'],
    queryFn: scanService.getEscalations,
    enabled: tab === 'escalations',
  })

  const scan = useMutation({
    mutationFn: () =>
      scanService.scanMessage({
        content: content.trim(),
        message_type: messageType,
        sender: sender.trim() || null,
      }),
    onSuccess: (data) => {
      setLatestResult(data)
      qc.invalidateQueries({ queryKey: ['scan', 'history'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const batchJudge = useMutation({
    mutationFn: () => scanService.batchJudge({ limit: 20 }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scan', 'history'] }),
  })

  const statusUpdate = useMutation({
    mutationFn: ({ scanId, newStatus }: { scanId: string; newStatus: ThreatStatus }) =>
      scanService.updateStatus(scanId, { status: newStatus }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scan', 'history'] })
      qc.invalidateQueries({ queryKey: ['scan', 'escalations'] })
    },
  })

  function handleStatusUpdate(scanId: string, newStatus: ThreatStatus) {
    statusUpdate.mutate({ scanId, newStatus })
  }

  function handleRefresh() {
    qc.invalidateQueries({ queryKey: ['scan', 'history'] })
    qc.invalidateQueries({ queryKey: ['scan', 'escalations'] })
  }

  const canScan = content.trim().length > 0 && !scan.isPending

  const STATUS_FILTER_OPTIONS: Array<{ value: ThreatStatus | 'ALL'; label: string }> = [
    { value: 'ALL', label: 'Any status' },
    { value: 'new', label: 'New' },
    { value: 'reviewing', label: 'Reviewing' },
    { value: 'escalated', label: 'Escalated' },
    { value: 'resolved', label: 'Resolved' },
    { value: 'closed', label: 'Closed' },
  ]

  return (
    <div className="max-w-6xl">
      <div className="mb-8 flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Threats</h1>
          <p className="text-slate-500 text-sm">Scan messages live and manage the full threat lifecycle.</p>
        </div>
        {isAdmin && (
          <Button
            onClick={() => batchJudge.mutate()}
            disabled={batchJudge.isPending}
            className="bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs h-9 px-3"
          >
            {batchJudge.isPending ? (
              <><Loader2 className="size-3 animate-spin mr-1.5" />Running…</>
            ) : (
              <><Layers className="size-3 mr-1.5" />Batch Judge</>
            )}
          </Button>
        )}
      </div>

      <div className="flex gap-1 mb-6 border-b border-slate-800">
        {([['scan', 'Scan & History'], ['escalations', 'Escalations']] as [TabKey, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 ${
              tab === key
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'scan' && (
        <>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-8">
            <div className="flex items-center gap-2 mb-4">
              <ShieldAlert className="size-4 text-blue-400" />
              <h2 className="text-sm font-semibold text-white">Scan a message</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1.5">Message type</label>
                <select
                  value={messageType}
                  onChange={(e) => setMessageType(e.target.value as MessageType)}
                  className="w-full h-10 bg-slate-950 border border-slate-700 rounded-md px-3 text-sm text-white focus:outline-none focus:border-blue-500/60"
                >
                  {MESSAGE_TYPES.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-2">
                <label className="text-xs text-slate-400 block mb-1.5">Sender (optional)</label>
                <Input
                  placeholder="e.g. +2348030001234 or BANK-ALERT"
                  value={sender}
                  onChange={(e) => setSender(e.target.value)}
                  className="bg-slate-950 border-slate-700 text-white placeholder-slate-600 h-10"
                />
              </div>
            </div>

            <div className="mb-3">
              <label className="text-xs text-slate-400 block mb-1.5">Message content</label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={4}
                placeholder="URGENT: Your GTBank account has been suspended. Verify your BVN at gtb-secure-verify.com or face permanent closure."
                className="w-full bg-slate-950 border border-slate-700 rounded-md px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/60 resize-none"
              />
            </div>

            {scan.error && (
              <div className="mb-3 flex items-start gap-2.5 px-3.5 py-3 rounded-lg bg-red-500/8 border border-red-500/20 text-sm text-red-400">
                <AlertCircle className="size-4 shrink-0 mt-0.5" />
                <span>{getApiErrorMessage(scan.error)}</span>
              </div>
            )}

            <Button
              onClick={() => scan.mutate()}
              disabled={!canScan}
              className="bg-blue-600 hover:bg-blue-500 text-white border-0 h-10 px-4 text-sm font-medium disabled:opacity-50"
            >
              {scan.isPending ? (
                <span className="flex items-center gap-2"><Loader2 className="size-4 animate-spin" />Scanning…</span>
              ) : (
                <span className="flex items-center gap-1.5"><Send className="size-3.5" />Run scan</span>
              )}
            </Button>

            {latestResult && (
              <div className="mt-5 pt-5 border-t border-slate-800">
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-3 font-semibold">Latest result</p>
                <ScanResultCard result={latestResult} onStatusUpdate={handleStatusUpdate} onRefresh={handleRefresh} />
              </div>
            )}
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl">
            <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between flex-wrap gap-3">
              <h2 className="text-sm font-semibold text-white">Scan history</h2>
              <div className="flex items-center gap-3 flex-wrap">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as ThreatStatus | 'ALL')}
                  className="h-8 bg-slate-950 border border-slate-700 rounded-md px-2 text-xs text-slate-300 focus:outline-none focus:border-blue-500/60"
                >
                  {STATUS_FILTER_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
                <div className="flex items-center gap-1">
                  {THREAT_FILTERS.map((filter) => (
                    <button
                      key={filter.value}
                      onClick={() => setThreatFilter(filter.value)}
                      className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                        threatFilter === filter.value
                          ? 'bg-blue-500/15 text-blue-400 border border-blue-500/25'
                          : 'text-slate-500 hover:text-slate-300 border border-transparent'
                      }`}
                    >
                      {filter.label}
                    </button>
                  ))}
                </div>
                <button onClick={handleRefresh} className="text-slate-500 hover:text-slate-300 transition-colors" title="Refresh">
                  <RefreshCw className="size-3.5" />
                </button>
              </div>
            </div>

            {history.isLoading ? (
              <div className="flex items-center justify-center py-16 text-slate-500">
                <Loader2 className="size-4 animate-spin mr-2" />Loading history…
              </div>
            ) : (history.data?.items.length ?? 0) === 0 ? (
              <div className="text-center py-16 text-slate-500 text-sm">No scans match this filter.</div>
            ) : (
              <div className="divide-y divide-slate-800">
                {history.data?.items.map((item) => (
                  <div key={item.id} className="px-5 py-3 hover:bg-slate-800/30 transition-colors">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <RiskBadge level={item.threat_level} />
                          <span className="text-[10px] font-semibold bg-slate-800 px-1.5 py-0.5 rounded text-slate-400 uppercase">
                            {item.action}
                          </span>
                          <StatusBadge
                            status={(item.threat_status as ThreatStatus) || 'new'}
                            scanId={item.id}
                            onUpdate={handleStatusUpdate}
                          />
                          <span className="text-xs text-slate-600 ml-auto">
                            {formatRelativeTime(item.created_at)}
                          </span>
                        </div>
                        <p className="text-sm text-slate-300 line-clamp-2">{item.reasoning}</p>
                        {item.flags.length > 0 && (
                          <div className="mt-1.5 flex flex-wrap gap-1">
                            {item.flags.slice(0, 5).map((flag) => (
                              <span key={flag} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                                {flag}
                              </span>
                            ))}
                          </div>
                        )}
                        {item.suggested_actions && item.suggested_actions.length > 0 && (
                          <SuggestedActions actions={item.suggested_actions} />
                        )}
                      </div>
                      <div className="shrink-0">
                        <ScoreBar score={item.risk_score} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {tab === 'escalations' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl">
          <div className="px-5 py-4 border-b border-slate-800">
            <h2 className="text-sm font-semibold text-white">Active escalations</h2>
            <p className="text-xs text-slate-500 mt-0.5">Threats currently in escalated state.</p>
          </div>
          {escalations.isLoading ? (
            <div className="flex items-center justify-center py-16 text-slate-500">
              <Loader2 className="size-4 animate-spin mr-2" />Loading escalations…
            </div>
          ) : (escalations.data?.escalations?.length ?? 0) === 0 ? (
            <div className="text-center py-16 text-slate-500 text-sm">No active escalations.</div>
          ) : (
            <div className="divide-y divide-slate-800">
              {(escalations.data?.escalations as any[])?.map((esc: any) => (
                <div key={esc.escalation_id} className="px-5 py-4">
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <div>
                      <span className="text-xs text-red-400 font-semibold uppercase">Escalated</span>
                      <span className="ml-2 text-xs text-slate-500">by {esc.escalated_by?.email || esc.escalated_by?.id}</span>
                      {esc.escalated_to && (
                        <span className="ml-1 text-xs text-slate-500">→ {esc.escalated_to.email}</span>
                      )}
                    </div>
                    <span className="text-xs text-slate-600">{formatRelativeTime(esc.created_at)}</span>
                  </div>
                  <p className="text-sm text-slate-300 mb-2">{esc.reason}</p>
                  {esc.scan && (
                    <div className="bg-slate-800/40 rounded-lg px-3 py-2">
                      <div className="flex items-center gap-2 mb-1">
                        <RiskBadge level={esc.scan.threat_level} />
                        <span className="text-xs text-slate-500 font-mono truncate">{esc.scan.content?.slice(0, 80)}</span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}