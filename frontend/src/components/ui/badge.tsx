import { cn } from '@/lib/utils'
import type { ThreatLevel } from '@/types'
import type { UserRole } from '@/features/auth/types'

const threatClasses: Record<ThreatLevel, string> = {
  HIGH:   'bg-red-500/12 text-red-400 border-red-500/25',
  MEDIUM: 'bg-orange-500/12 text-orange-400 border-orange-500/25',
  LOW:    'bg-yellow-500/12 text-yellow-400 border-yellow-500/25',
  CLEAN:  'bg-emerald-500/12 text-emerald-400 border-emerald-500/25',
}

const roleClasses: Record<UserRole, string> = {
  admin:   'bg-purple-500/12 text-purple-400 border-purple-500/25',
  analyst: 'bg-blue-500/12 text-blue-400 border-blue-500/25',
  viewer:  'bg-slate-500/12 text-slate-400 border-slate-500/25',
}

interface BadgeProps {
  children: React.ReactNode
  threat?: ThreatLevel
  role?: UserRole
  className?: string
}

export function Badge({ children, threat, role, className }: BadgeProps) {
  const colorClass = threat
    ? threatClasses[threat]
    : role
    ? roleClasses[role]
    : 'bg-slate-500/12 text-slate-400 border-slate-500/25'

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold border tracking-wide',
        colorClass,
        className,
      )}
    >
      {children}
    </span>
  )
}
