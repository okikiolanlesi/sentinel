import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, AlertCircle, UserPlus, X, CheckCircle2, Copy, Power } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { usersService, type BackendUserSummary, type InviteUserResponse } from '@/services/users.service'
import type { UserRole } from '@/features/auth/types'
import { getApiErrorMessage } from '@/lib/errors'
import { formatRelativeTime } from '@/lib/format'

const ROLES: UserRole[] = ['admin', 'analyst', 'viewer']

const roleStyles: Record<UserRole, string> = {
  admin: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
  analyst: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  viewer: 'bg-slate-500/15 text-slate-400 border-slate-500/30',
}

function RoleBadge({ role }: { role: UserRole }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md border text-[11px] font-semibold tracking-wide uppercase ${roleStyles[role]}`}>
      {role}
    </span>
  )
}

function InviteModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [role, setRole] = useState<UserRole>('analyst')
  const [result, setResult] = useState<InviteUserResponse | null>(null)
  const [copied, setCopied] = useState(false)

  const invite = useMutation({
    mutationFn: () =>
      usersService.invite({
        email: email.trim(),
        full_name: fullName.trim() || undefined,
        role,
      }),
    onSuccess: (data) => {
      setResult(data)
      qc.invalidateQueries({ queryKey: ['users', 'list'] })
    },
  })

  function copyCreds() {
    if (!result) return
    const text = `Email: ${result.temporary_credentials.email}\nPassword: ${result.temporary_credentials.temporary_password}`
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-5">
          <div>
            <h3 className="text-lg font-bold text-white">Invite team member</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Account created instantly with a temporary password.
            </p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white">
            <X className="size-4" />
          </button>
        </div>

        {result ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-emerald-400 text-sm">
              <CheckCircle2 className="size-4" />
              {result.message}
            </div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 space-y-2">
              <div>
                <p className="text-[11px] text-slate-500 uppercase tracking-wider mb-0.5">Email</p>
                <p className="text-sm text-white font-mono">{result.temporary_credentials.email}</p>
              </div>
              <div>
                <p className="text-[11px] text-slate-500 uppercase tracking-wider mb-0.5">Temporary password</p>
                <p className="text-sm text-white font-mono break-all">{result.temporary_credentials.temporary_password}</p>
              </div>
            </div>
            <p className="text-xs text-amber-400 leading-relaxed">⚠ {result.temporary_credentials.warning}</p>
            <div className="flex gap-2">
              <Button onClick={copyCreds} className="bg-slate-800 hover:bg-slate-700 text-white border-0 h-9 px-3 text-sm flex-1">
                <Copy className="size-3.5 mr-1.5" />
                {copied ? 'Copied!' : 'Copy credentials'}
              </Button>
              <Button onClick={onClose} className="bg-blue-600 hover:bg-blue-500 text-white border-0 h-9 px-3 text-sm">
                Done
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1.5">Email</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="teammate@company.com"
                className="bg-slate-950 border-slate-700 text-white h-10"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1.5">Full name (optional)</label>
              <Input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Ada Okafor"
                className="bg-slate-950 border-slate-700 text-white h-10"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1.5">Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
                className="w-full h-10 bg-slate-950 border border-slate-700 rounded-md px-3 text-sm text-white focus:outline-none focus:border-blue-500/60 capitalize"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>

            {invite.error && (
              <div className="flex items-start gap-2.5 px-3 py-2.5 rounded-lg bg-red-500/8 border border-red-500/20 text-sm text-red-400">
                <AlertCircle className="size-4 shrink-0 mt-0.5" />
                <span>{getApiErrorMessage(invite.error)}</span>
              </div>
            )}

            <Button
              onClick={() => invite.mutate()}
              disabled={!email.trim() || invite.isPending}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white border-0 h-10 text-sm font-medium disabled:opacity-50"
            >
              {invite.isPending ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="size-4 animate-spin" />
                  Creating…
                </span>
              ) : (
                'Invite user'
              )}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function UserManagementPage() {
  const qc = useQueryClient()
  const [showInvite, setShowInvite] = useState(false)

  const list = useQuery({
    queryKey: ['users', 'list'],
    queryFn: () => usersService.list(1, 100),
  })

  const changeRole = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: UserRole }) =>
      usersService.changeRole(userId, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users', 'list'] }),
  })

  const toggleActive = useMutation({
    mutationFn: (user: BackendUserSummary) =>
      user.is_active ? usersService.deactivate(user.id) : usersService.activate(user.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users', 'list'] }),
  })

  return (
    <div className="max-w-6xl">
      <div className="mb-8 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">User Management</h1>
          <p className="text-slate-500 text-sm">Manage team members, roles, and access. Admin only.</p>
        </div>
        <Button
          onClick={() => setShowInvite(true)}
          className="bg-blue-600 hover:bg-blue-500 text-white border-0 h-10 px-4 text-sm font-medium"
        >
          <UserPlus className="size-3.5 mr-1.5" />
          Invite user
        </Button>
      </div>

      {(list.error || changeRole.error || toggleActive.error) && (
        <div className="mb-5 flex items-start gap-2.5 px-3.5 py-3 rounded-lg bg-red-500/8 border border-red-500/20 text-sm text-red-400">
          <AlertCircle className="size-4 shrink-0 mt-0.5" />
          <span>{getApiErrorMessage(list.error || changeRole.error || toggleActive.error)}</span>
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-xl">
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Team members</h2>
          <span className="text-xs text-slate-500">
            {list.data?.total ?? 0} {list.data?.total === 1 ? 'user' : 'users'}
          </span>
        </div>

        {list.isLoading ? (
          <div className="flex items-center justify-center py-16 text-slate-500">
            <Loader2 className="size-4 animate-spin mr-2" />
            Loading users…
          </div>
        ) : (list.data?.users.length ?? 0) === 0 ? (
          <div className="text-center py-16 text-slate-500 text-sm">
            No users yet. Click "Invite user" to add the first one.
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {list.data?.users.map((user) => (
              <div
                key={user.id}
                className={`px-5 py-3 transition-colors ${user.is_active ? 'hover:bg-slate-800/30' : 'opacity-50'}`}
              >
                <div className="flex items-center gap-4">
                  <div className="size-9 rounded-full bg-linear-to-br from-blue-500 to-purple-500 flex items-center justify-center text-xs font-bold text-white shrink-0">
                    {(user.full_name || user.email).slice(0, 2).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-white truncate">{user.full_name || user.email}</span>
                      <RoleBadge role={user.role} />
                      {!user.is_active && (
                        <span className="text-[10px] uppercase tracking-wider text-rose-400 font-bold">Deactivated</span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="text-xs text-slate-500 truncate">{user.email}</span>
                      {user.last_login && (
                        <span className="text-xs text-slate-600">· last seen {formatRelativeTime(user.last_login)}</span>
                      )}
                    </div>
                  </div>
                  <div className="shrink-0 flex items-center gap-2">
                    <select
                      value={user.role}
                      onChange={(e) => changeRole.mutate({ userId: user.id, role: e.target.value as UserRole })}
                      disabled={!user.is_active || changeRole.isPending}
                      className="h-8 bg-slate-950 border border-slate-700 rounded-md px-2 text-xs text-white capitalize disabled:opacity-50 focus:outline-none focus:border-blue-500/60"
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>{r}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => toggleActive.mutate(user)}
                      disabled={toggleActive.isPending}
                      className={`p-1.5 rounded-md border transition-colors disabled:opacity-50 ${
                        user.is_active
                          ? 'text-slate-400 hover:text-rose-400 border-slate-700 hover:border-rose-500/30'
                          : 'text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10'
                      }`}
                      aria-label={user.is_active ? 'Deactivate' : 'Reactivate'}
                      title={user.is_active ? 'Deactivate' : 'Reactivate'}
                    >
                      <Power className="size-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showInvite && <InviteModal onClose={() => setShowInvite(false)} />}
    </div>
  )
}