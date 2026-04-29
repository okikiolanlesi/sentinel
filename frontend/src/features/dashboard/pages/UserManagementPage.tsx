import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Users, UserPlus, MoreHorizontal, ShieldCheck, ShieldOff, Trash2, AlertCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Dialog } from '@/components/ui/dialog'
import { Select } from '@/components/ui/select'
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from '@/components/ui/form'
import { useUsers } from '@/features/users/hooks/useUsers'
import { useInviteUser } from '@/features/users/hooks/useInviteUser'
import { useChangeUserRole } from '@/features/users/hooks/useChangeUserRole'
import { useDeactivateUser } from '@/features/users/hooks/useDeactivateUser'
import { useActivateUser } from '@/features/users/hooks/useActivateUser'
import { useDeleteUser } from '@/features/users/hooks/useDeleteUser'
import { getApiErrorMessage } from '@/lib/errors'
import type { ApiUser } from '@/features/users/types'
import type { UserRole } from '@/features/auth/types'

const roleOptions = [
  { value: 'admin',   label: 'Admin' },
  { value: 'analyst', label: 'Analyst' },
  { value: 'viewer',  label: 'Viewer' },
]

const inviteSchema = z.object({
  full_name:    z.string().trim().min(1, 'Name is required'),
  email:        z.string().min(1, 'Email is required').email('Enter a valid email'),
  organisation: z.string().trim().min(1, 'Organisation is required'),
  role:         z.enum(['admin', 'analyst', 'viewer']),
})
type InviteFormData = z.infer<typeof inviteSchema>

function formatDate(iso?: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function ActionsMenu({ user }: { user: ApiUser }) {
  const [open, setOpen] = useState(false)
  const { mutate: changeRole } = useChangeUserRole()
  const { mutate: deactivate, isPending: deactivating } = useDeactivateUser()
  const { mutate: activate, isPending: activating } = useActivateUser()
  const { mutate: deleteUser, isPending: deleting } = useDeleteUser()

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((p) => !p)}
        className="p-1.5 rounded-md text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
      >
        <MoreHorizontal className="size-4" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-8 z-20 w-44 bg-slate-800 border border-slate-700 rounded-lg shadow-xl py-1">
            <div className="px-3 py-1.5 border-b border-slate-700 mb-1">
              <p className="text-[11px] text-slate-500 font-medium uppercase tracking-wide">Change role</p>
            </div>
            {roleOptions.filter((r) => r.value !== user.role).map((r) => (
              <button
                key={r.value}
                onClick={() => { changeRole({ userId: user.id, role: r.value as UserRole }); setOpen(false) }}
                className="w-full text-left px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700/60 transition-colors"
              >
                Set as {r.label}
              </button>
            ))}
            <div className="border-t border-slate-700 mt-1 pt-1">
              {user.is_active ? (
                <button
                  onClick={() => { deactivate(user.id); setOpen(false) }}
                  disabled={deactivating}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-amber-400 hover:bg-slate-700/60 transition-colors"
                >
                  <ShieldOff className="size-3.5" /> Deactivate
                </button>
              ) : (
                <button
                  onClick={() => { activate(user.id); setOpen(false) }}
                  disabled={activating}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-emerald-400 hover:bg-slate-700/60 transition-colors"
                >
                  <ShieldCheck className="size-3.5" /> Activate
                </button>
              )}
              <button
                onClick={() => { deleteUser(user.id); setOpen(false) }}
                disabled={deleting}
                className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-red-400 hover:bg-slate-700/60 transition-colors"
              >
                <Trash2 className="size-3.5" /> Delete
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default function UserManagementPage() {
  const [inviteOpen, setInviteOpen] = useState(false)
  const [tempCreds, setTempCreds] = useState<{ email: string; temporary_password: string } | null>(null)

  const { data, isLoading, error: loadError } = useUsers()
  const { mutate: invite, isPending: inviting, error: inviteError, reset: resetInvite } = useInviteUser()

  const form = useForm<InviteFormData>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { full_name: '', email: '', organisation: '', role: 'analyst' },
    mode: 'onChange',
  })

  function onInvite(data: InviteFormData) {
    resetInvite()
    invite(data, {
      onSuccess: (res) => {
        setInviteOpen(false)
        form.reset()
        setTempCreds(res.temporary_credentials)
      },
    })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-7">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-slate-800 border border-slate-700">
            <Users className="size-4 text-slate-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">User Management</h1>
            <p className="text-slate-500 text-xs mt-0.5">
              {data ? `${data.total} member${data.total !== 1 ? 's' : ''}` : 'Manage team access'}
            </p>
          </div>
        </div>
        <Button
          onClick={() => setInviteOpen(true)}
          className="bg-blue-600 hover:bg-blue-500 text-white border-0 h-9 px-4 text-sm font-medium"
        >
          <UserPlus className="size-3.5 mr-1.5" />
          Invite user
        </Button>
      </div>

      {loadError && (
        <div className="flex items-center gap-2.5 px-4 py-3 rounded-lg bg-red-500/8 border border-red-500/20 text-sm text-red-400 mb-5">
          <AlertCircle className="size-4 shrink-0" />
          {getApiErrorMessage(loadError)}
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-800">
              <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wide">User</th>
              <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Organisation</th>
              <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Role</th>
              <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">Last login</th>
              <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-slate-500 text-sm">
                  <span className="inline-block size-5 rounded-full border-2 border-slate-700 border-t-blue-400 animate-spin" />
                </td>
              </tr>
            )}
            {!isLoading && data?.users.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-slate-500 text-sm">No users found.</td>
              </tr>
            )}
            {data?.users.map((user) => (
              <tr key={user.id} className="border-b border-slate-800/60 last:border-0 hover:bg-slate-800/20 transition-colors">
                <td className="px-4 py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="size-7 rounded-full bg-linear-to-br from-blue-500 to-purple-500 flex items-center justify-center text-[10px] font-bold text-white shrink-0">
                      {user.full_name?.slice(0, 2).toUpperCase() ?? '?'}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-white">{user.full_name || '—'}</div>
                      <div className="text-xs text-slate-500">{user.email}</div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3.5 text-sm text-slate-400 hidden md:table-cell">{user.organisation}</td>
                <td className="px-4 py-3.5">
                  <Badge role={user.role}>{user.role}</Badge>
                </td>
                <td className="px-4 py-3.5 text-sm text-slate-500 hidden lg:table-cell">{formatDate(user.last_login)}</td>
                <td className="px-4 py-3.5">
                  <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${user.is_active ? 'text-emerald-400' : 'text-slate-500'}`}>
                    <span className={`size-1.5 rounded-full ${user.is_active ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-4 py-3.5">
                  <ActionsMenu user={user} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Invite dialog */}
      <Dialog open={inviteOpen} onClose={() => { setInviteOpen(false); form.reset(); resetInvite() }} title="Invite team member">
        {inviteError && (
          <div className="flex items-start gap-2 mb-4 px-3 py-2.5 rounded-lg bg-red-500/8 border border-red-500/20 text-xs text-red-400">
            <AlertCircle className="size-3.5 shrink-0 mt-0.5" />
            {getApiErrorMessage(inviteError)}
          </div>
        )}
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onInvite)} noValidate className="space-y-3.5">
            <FormField control={form.control} name="full_name" render={({ field }) => (
              <FormItem>
                <FormLabel className="text-slate-300 text-sm">Full name</FormLabel>
                <FormControl>
                  <Input placeholder="Ada Okafor" className="bg-slate-800 border-slate-700 text-white placeholder-slate-600 focus-visible:border-blue-500/60 focus-visible:ring-blue-500/20 h-10" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="email" render={({ field }) => (
              <FormItem>
                <FormLabel className="text-slate-300 text-sm">Email</FormLabel>
                <FormControl>
                  <Input type="email" placeholder="ada@company.com" className="bg-slate-800 border-slate-700 text-white placeholder-slate-600 focus-visible:border-blue-500/60 focus-visible:ring-blue-500/20 h-10" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="organisation" render={({ field }) => (
              <FormItem>
                <FormLabel className="text-slate-300 text-sm">Organisation</FormLabel>
                <FormControl>
                  <Input placeholder="Acme Telecom Ltd" className="bg-slate-800 border-slate-700 text-white placeholder-slate-600 focus-visible:border-blue-500/60 focus-visible:ring-blue-500/20 h-10" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="role" render={({ field }) => (
              <FormItem>
                <FormLabel className="text-slate-300 text-sm">Role</FormLabel>
                <FormControl>
                  <Select options={roleOptions} value={field.value} onChange={field.onChange} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <div className="flex gap-2.5 pt-1">
              <Button type="button" onClick={() => { setInviteOpen(false); form.reset() }} className="flex-1 bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 h-9 text-sm">Cancel</Button>
              <Button type="submit" disabled={inviting} className="flex-1 bg-blue-600 hover:bg-blue-500 text-white border-0 h-9 text-sm disabled:opacity-60">
                {inviting ? 'Inviting…' : 'Send invite'}
              </Button>
            </div>
          </form>
        </Form>
      </Dialog>

      {/* Temp credentials dialog */}
      <Dialog open={!!tempCreds} onClose={() => setTempCreds(null)} title="Invitation sent">
        <div className="space-y-4">
          <p className="text-sm text-slate-400">Share these temporary credentials with the new user. They should change their password on first login.</p>
          <div className="space-y-2">
            {[
              { label: 'Email', value: tempCreds?.email },
              { label: 'Temporary password', value: tempCreds?.temporary_password },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="text-[11px] text-slate-500 mb-1">{label}</p>
                <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2">
                  <code className="text-sm text-emerald-400 font-mono">{value}</code>
                </div>
              </div>
            ))}
          </div>
          <Button onClick={() => setTempCreds(null)} className="w-full bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 h-9 text-sm">Done</Button>
        </div>
      </Dialog>
    </div>
  )
}
