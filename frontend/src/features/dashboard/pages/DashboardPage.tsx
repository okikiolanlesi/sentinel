import { useQuery } from '@tanstack/react-query'
import {
  Shield, AlertTriangle, ScanFace, Activity, Ban, Radio,
  Loader2, AlertCircle, CheckCircle2, Info, PenLine, Brain,
} from 'lucide-react'
import { dashboardService, type HealthCheck } from '@/services/dashboard.service'
import { scanService } from '@/services/scan.service'
import { RiskBadge, ScoreBar } from '@/components/RiskBadge'
import { formatNumber, formatRelativeTime } from '@/lib/format'
import { getApiErrorMessage } from '@/lib/errors'
import { useAuthStore } from '@/store/auth.store'

interface KpiCardProps {
  label: string
  value: string | number
  icon: React.ComponentType<{ className?: string }>
  accent: string
}

function KpiCard({ label, value, icon: Icon, accent }: KpiCardProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">{label}</span>
        <div className={`p-1.5 rounded-md ${accent}`}>
          <Icon className="size-4" />
        </div>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
    </div>
  )
}

function MessageTypePill({ type }: { type: string }) {
  return (
    <span className="text-[10px] font-semibold bg-slate-800 px-1.5 py-0.5 rounded text-slate-400 uppercase">
      {type}
    </span>
  )
}

const HEALTH_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  ok: CheckCircle2,
  healthy: CheckCircle2,
  warning: AlertTriangle,
  critical: AlertCircle,
  info: Info,
}

const HEALTH_COLORS: Record<string, string> = {
  ok: 'text-emerald-400',
  healthy: 'text-emerald-400',
  warning: 'text-amber-400',
  critical: 'text-red-400',
  info: 'text-blue-400',
}

const HEALTH_BG: Record<string, string> = {
  ok: 'bg-emerald-500/10 border-emerald-500/20',
  healthy: 'bg-emerald-500/10 border-emerald-500/20',
  warning: 'bg-amber-500/10 border-amber-500/20',
  critical: 'bg-red-500/10 border-red-500/20',
  info: 'bg-blue-500/10 border-blue-500/20',
}

function HealthWidget() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', 'health'],
    queryFn: dashboardService.getHealth,
    refetchInterval: 60_000,
  })

  if (isLoading) return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-center py-10">
      <Loader2 className="size-4 animate-spin text-slate-500" />
    </div>
  )

  if (error) return null

  const overall = data?.overall_status ?? 'healthy'
  const OverallIcon = HEALTH_ICONS[overall] ?? CheckCircle2

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-white">System health</h2>
        <span className={`flex items-center gap-1.5 text-xs font-semibold ${HEALTH_COLORS[overall]}`}>
          <OverallIcon className="size-3.5" />
          {overall.toUpperCase()}
        </span>
      </div>
      <div className="space-y-2">
        {data?.checks.map((check: HealthCheck) => {
          const Icon = HEALTH_ICONS[check.severity] ?? Info
          return (
            <div
              key={check.name}
              className={`flex items-start gap-3 px-3 py-2.5 rounded-lg border ${HEALTH_BG[check.severity]}`}
            >
              <Icon className={`size-3.5 shrink-0 mt-0.5 ${HEALTH_COLORS[check.severity]}`} />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-slate-300">{check.message}</p>
              </div>
              <span className={`text-xs font-mono shrink-0 ${HEALTH_COLORS[check.severity]}`}>
                {String(check.value)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function OrgMemoryWidget() {
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin'

  const { data, isLoading } = useQuery({
    queryKey: ['org', 'memory'],
    queryFn: dashboardService.getOrgMemory,
    enabled: isAdmin,
  })

  if (!isAdmin) return null

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Brain className="size-4 text-purple-400" />
        <h2 className="text-sm font-semibold text-white">Org fraud memory</h2>
      </div>
      {isLoading ? (
        <div className="flex items-center text-slate-500 text-xs gap-2">
          <Loader2 className="size-3 animate-spin" />Loading…
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-slate-800/40 rounded-lg p-3 text-center">
            <div className="text-xl font-bold text-white">{data?.stats?.total_patterns ?? 0}</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wide mt-0.5">Patterns</div>
          </div>
          <div className="bg-slate-800/40 rounded-lg p-3 text-center">
            <div className="text-xl font-bold text-white">{data?.stats?.patterns_added_this_week ?? 0}</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wide mt-0.5">This week</div>
          </div>
          <div className="bg-slate-800/40 rounded-lg p-3 text-center">
            <div className="text-xl font-bold text-white">{data?.stats?.top_senders?.length ?? 0}</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wide mt-0.5">Blocked senders</div>
          </div>
        </div>
      )}
    </div>
  )
}

function CorrectionsWidget() {
  const { user } = useAuthStore()
  const isAnalyst = user?.role === 'admin' || user?.role === 'analyst'

  const { data, isLoading } = useQuery({
    queryKey: ['scan', 'corrections', 'stats'],
    queryFn: scanService.getCorrectionStats,
    enabled: isAnalyst,
  })

  if (!isAnalyst) return null

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <PenLine className="size-4 text-amber-400" />
        <h2 className="text-sm font-semibold text-white">AI corrections this week</h2>
      </div>
      {isLoading ? (
        <div className="flex items-center text-slate-500 text-xs gap-2">
          <Loader2 className="size-3 animate-spin" />Loading…
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-slate-800/40 rounded-lg p-3 text-center">
            <div className="text-xl font-bold text-white">{data?.total_corrections_this_week ?? 0}</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wide mt-0.5">Total</div>
          </div>
          <div className="bg-slate-800/40 rounded-lg p-3 text-center">
            <div className="text-xl font-bold text-amber-400">{data?.false_positive_rate?.toFixed(1) ?? '0.0'}%</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wide mt-0.5">False +ve</div>
          </div>
          <div className="bg-slate-800/40 rounded-lg p-3 text-center">
            <div className="text-xl font-bold text-red-400">{data?.false_negative_rate?.toFixed(1) ?? '0.0'}%</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wide mt-0.5">False -ve</div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function DashboardPage() {
  const stats = useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: dashboardService.getStats,
    refetchInterval: 30_000,
  })

  const feed = useQuery({
    queryKey: ['dashboard', 'threat-feed'],
    queryFn: () => dashboardService.getThreatFeed(20),
    refetchInterval: 30_000,
  })

  const isLoading = stats.isLoading || feed.isLoading

  return (
    <div className="max-w-7xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-1">Dashboard</h1>
        <p className="text-slate-500 text-sm">
          Real-time overview of fraud intelligence activity. Auto-refreshes every 30 seconds.
        </p>
      </div>

      {(stats.error || feed.error) && (
        <div className="mb-6 flex items-start gap-2.5 px-3.5 py-3 rounded-lg bg-red-500/8 border border-red-500/20 text-sm text-red-400">
          <AlertCircle className="size-4 shrink-0 mt-0.5" />
          <span>{getApiErrorMessage(stats.error || feed.error)}</span>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-8">
        <KpiCard label="Total Scanned" value={isLoading ? '—' : formatNumber(stats.data?.total_scanned ?? 0)} icon={Activity} accent="bg-blue-500/15 text-blue-400" />
        <KpiCard label="Threats" value={isLoading ? '—' : formatNumber(stats.data?.threats_detected ?? 0)} icon={AlertTriangle} accent="bg-red-500/15 text-red-400" />
        <KpiCard label="Deepfakes" value={isLoading ? '—' : formatNumber(stats.data?.deepfakes_found ?? 0)} icon={ScanFace} accent="bg-purple-500/15 text-purple-400" />
        <KpiCard label="Avg Risk" value={isLoading ? '—' : (stats.data?.avg_risk_score ?? 0).toFixed(0)} icon={Shield} accent="bg-amber-500/15 text-amber-400" />
        <KpiCard label="Blocked Today" value={isLoading ? '—' : formatNumber(stats.data?.blocked_today ?? 0)} icon={Ban} accent="bg-rose-500/15 text-rose-400" />
        <KpiCard label="Active Campaigns" value={isLoading ? '—' : (stats.data?.active_campaigns ?? 0).toString()} icon={Radio} accent="bg-emerald-500/15 text-emerald-400" />
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-6">
        <h2 className="text-sm font-semibold text-white mb-4">Threat-level breakdown</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {(['HIGH', 'MEDIUM', 'LOW', 'CLEAN'] as const).map((level) => (
            <div key={level} className="flex items-center justify-between bg-slate-800/40 rounded-lg px-3 py-2.5">
              <RiskBadge level={level} />
              <span className="text-lg font-bold text-white">
                {isLoading ? '—' : stats.data?.breakdown?.[level] ?? 0}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <HealthWidget />
        <OrgMemoryWidget />
        <CorrectionsWidget />
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl">
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-white">Live threat feed</h2>
            <p className="text-xs text-slate-500 mt-0.5">Latest 20 scans across all channels</p>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Live
          </div>
        </div>

        {feed.isLoading ? (
          <div className="flex items-center justify-center py-16 text-slate-500">
            <Loader2 className="size-4 animate-spin mr-2" />
            Loading threats…
          </div>
        ) : (feed.data?.length ?? 0) === 0 ? (
          <div className="text-center py-16 text-slate-500 text-sm">
            No scans yet. Run your first scan from the Threats page.
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {feed.data?.map((item) => (
              <div key={item.id} className="px-5 py-3 hover:bg-slate-800/30 transition-colors">
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <RiskBadge level={item.threat_level} />
                      <MessageTypePill type={item.message_type} />
                      {item.sender && (
                        <span className="text-xs text-slate-500 font-mono truncate">{item.sender}</span>
                      )}
                      <span className="text-xs text-slate-600 ml-auto">
                        {formatRelativeTime(item.created_at)}
                      </span>
                    </div>
                    <p className="text-sm text-slate-300 truncate">{item.content_preview}</p>
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
    </div>
  )
}