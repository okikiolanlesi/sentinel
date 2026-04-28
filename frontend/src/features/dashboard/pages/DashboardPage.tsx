import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  ShieldAlert,
  ScanFace,
  Activity,
  Zap,
  TrendingUp,
  Radio,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useDashboardStats } from "@/features/dashboard/hooks/useDashboardStats";
import { useThreatFeed } from "@/features/dashboard/hooks/useThreatFeed";
import { useTrends } from "@/features/dashboard/hooks/useTrends";
import type { ThreatLevel } from "@/types";

const breakdownOrder: ThreatLevel[] = ["HIGH", "MEDIUM", "LOW", "CLEAN"];
const breakdownColors: Record<ThreatLevel, string> = {
  HIGH: "bg-red-500",
  MEDIUM: "bg-orange-500",
  LOW: "bg-yellow-500",
  CLEAN: "bg-emerald-500",
};

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  iconClass,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  iconClass?: string;
}) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs text-slate-500 font-medium">{label}</p>
        <div className={`p-1.5 rounded-lg bg-slate-800 ${iconClass ?? ""}`}>
          <Icon className="size-3.5 text-current" />
        </div>
      </div>
      <p className="text-2xl font-bold text-white">
        {typeof value === "number" ? value.toLocaleString() : value}
      </p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 shadow-xl text-xs">
      <p className="text-slate-400 mb-1.5">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="font-medium">
          {p.name}: {p.value.toLocaleString()}
        </p>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: feed, isLoading: feedLoading } = useThreatFeed(10);
  const { data: trends, isLoading: trendsLoading } = useTrends(30);

  const chartData = trends?.trends.map((t) => ({
    date: new Date(t.date).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
    }),
    Scanned: t.total_scanned,
    Threats: t.threats_detected,
  }));

  return (
    <div className="space-y-6">
      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statsLoading
          ? Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5 h-24 animate-pulse"
              />
            ))
          : stats && (
              <>
                <StatCard
                  label="Total scanned"
                  value={stats.total_scanned}
                  icon={Activity}
                  iconClass="text-blue-400"
                />
                <StatCard
                  label="Threats detected"
                  value={stats.threats_detected}
                  icon={ShieldAlert}
                  iconClass="text-red-400"
                />
                <StatCard
                  label="Deepfakes found"
                  value={stats.deepfakes_found}
                  icon={ScanFace}
                  iconClass="text-purple-400"
                />
                <StatCard
                  label="Avg risk score"
                  value={stats.avg_risk_score.toFixed(1)}
                  icon={TrendingUp}
                  iconClass="text-amber-400"
                  sub="out of 100"
                />
              </>
            )}
      </div>

      {/* Breakdown + Trend chart */}
      <div className="grid lg:grid-cols-3 gap-4">
        {/* Breakdown */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <p className="text-sm font-medium text-slate-300 mb-4">
            Threat breakdown
          </p>
          {statsLoading ? (
            <div className="space-y-3">
              {breakdownOrder.map((l) => (
                <div
                  key={l}
                  className="h-8 bg-slate-800 rounded animate-pulse"
                />
              ))}
            </div>
          ) : (
            stats && (
              <div className="space-y-3">
                {breakdownOrder.map((level) => {
                  const count = stats.breakdown[level] ?? 0;
                  const total = Object.values(stats.breakdown).reduce(
                    (a, b) => a + b,
                    0,
                  );
                  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                  return (
                    <div key={level}>
                      <div className="flex justify-between mb-1">
                        <Badge threat={level}>{level}</Badge>
                        <span className="text-xs text-slate-400">
                          {count.toLocaleString()}{" "}
                          <span className="text-slate-600">({pct}%)</span>
                        </span>
                      </div>
                      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${breakdownColors[level]}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )
          )}
        </div>

        {/* Trend chart */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5">
          <p className="text-sm font-medium text-slate-300 mb-4">
            30-day activity
          </p>
          {trendsLoading ? (
            <div className="h-48 bg-slate-800 rounded animate-pulse" />
          ) : (
            <ResponsiveContainer width="100%" height={192}>
              <AreaChart
                data={chartData}
                margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="gScanned" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gThreats" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip content={<ChartTooltip />} />
                <Legend
                  iconType="circle"
                  iconSize={6}
                  wrapperStyle={{ fontSize: "11px", color: "#94a3b8" }}
                />
                <Area
                  type="monotone"
                  dataKey="Scanned"
                  stroke="#3b82f6"
                  strokeWidth={1.5}
                  fill="url(#gScanned)"
                  dot={false}
                />
                <Area
                  type="monotone"
                  dataKey="Threats"
                  stroke="#ef4444"
                  strokeWidth={1.5}
                  fill="url(#gThreats)"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Live threat feed */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="flex items-center gap-2.5 px-5 py-4 border-b border-slate-800">
          <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
          <p className="text-sm font-medium text-slate-300">Live threat feed</p>
          <span className="text-xs text-slate-600 ml-auto">
            Refreshes every 30s
          </span>
        </div>

        {feedLoading && (
          <div className="py-10 text-center">
            <span className="inline-block size-5 rounded-full border-2 border-slate-700 border-t-blue-400 animate-spin" />
          </div>
        )}
        {!feedLoading && feed?.items.length === 0 && (
          <p className="px-5 py-10 text-center text-slate-500 text-sm">
            No recent threats.
          </p>
        )}

        <div className="divide-y divide-slate-800/60">
          {feed?.items.map((item) => (
            <div key={item.id} className="flex items-center gap-4 px-5 py-3.5">
              <Badge threat={item.threat_level}>{item.threat_level}</Badge>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-300 truncate">
                  {item.content_preview}
                </p>
                <p className="text-[11px] text-slate-600 mt-0.5">
                  {item.sender} · {item.message_type?.toUpperCase()}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-sm font-mono font-semibold text-white">
                  {item.risk_score.toFixed(0)}
                </p>
                <p className="text-[11px] text-slate-600">
                  {new Date(item.created_at).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
