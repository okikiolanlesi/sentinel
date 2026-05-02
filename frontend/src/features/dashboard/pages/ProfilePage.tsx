import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, AlertCircle, CheckCircle2, User as UserIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { usersService } from '@/services/users.service'
import { useAuthStore } from '@/store/auth.store'
import { mapBackendUser } from '@/services/auth.service'
import { getApiErrorMessage } from '@/lib/errors'
import { formatRelativeTime } from '@/lib/format'

const roleStyles = {
  admin: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
  analyst: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  viewer: 'bg-slate-500/15 text-slate-400 border-slate-500/30',
}

export default function ProfilePage() {
  const qc = useQueryClient()
  const { user, setAuth, token } = useAuthStore()
  const [fullName, setFullName] = useState('')
  const [organisation, setOrganisation] = useState('')
  const [savedFlash, setSavedFlash] = useState(false)

  const me = useQuery({
    queryKey: ['users', 'me'],
    queryFn: usersService.getMe,
  })

  useEffect(() => {
    if (me.data) {
      setFullName(me.data.full_name ?? '')
      setOrganisation(me.data.organisation ?? '')
    }
  }, [me.data])

  const update = useMutation({
    mutationFn: () =>
      usersService.updateMe({
        full_name: fullName.trim() || undefined,
        organisation: organisation.trim() || undefined,
      }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['users', 'me'] })
      if (token) setAuth(mapBackendUser(data), token)
      setSavedFlash(true)
      setTimeout(() => setSavedFlash(false), 2500)
    },
  })

  const isDirty =
    (me.data?.full_name ?? '') !== fullName.trim() ||
    (me.data?.organisation ?? '') !== organisation.trim()

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-1">Profile</h1>
        <p className="text-slate-500 text-sm">Update your name and organisation.</p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        {me.isLoading ? (
          <div className="flex items-center justify-center py-12 text-slate-500">
            <Loader2 className="size-4 animate-spin mr-2" />
            Loading profile…
          </div>
        ) : me.error ? (
          <div className="flex items-start gap-2.5 px-3.5 py-3 rounded-lg bg-red-500/8 border border-red-500/20 text-sm text-red-400">
            <AlertCircle className="size-4 shrink-0 mt-0.5" />
            <span>{getApiErrorMessage(me.error)}</span>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-4 mb-6 pb-6 border-b border-slate-800">
              <div className="size-14 rounded-full bg-linear-to-br from-blue-500 to-purple-500 flex items-center justify-center text-lg font-bold text-white">
                {(me.data?.full_name || me.data?.email || '?').slice(0, 2).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{me.data?.email}</p>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  {me.data && (
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-md border text-[11px] font-semibold tracking-wide uppercase ${roleStyles[me.data.role]}`}
                    >
                      {me.data.role}
                    </span>
                  )}
                  {me.data?.last_login && (
                    <span className="text-xs text-slate-500">
                      Last login {formatRelativeTime(me.data.last_login)}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1.5">Full name</label>
                <Input
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Ada Okafor"
                  className="bg-slate-950 border-slate-700 text-white h-10"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1.5">Organisation</label>
                <Input
                  value={organisation}
                  onChange={(e) => setOrganisation(e.target.value)}
                  placeholder="Acme Telecom Ltd"
                  className="bg-slate-950 border-slate-700 text-white h-10"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1.5">Email</label>
                <Input
                  value={me.data?.email ?? ''}
                  disabled
                  className="bg-slate-950 border-slate-800 text-slate-500 h-10"
                />
                <p className="text-[11px] text-slate-600 mt-1">
                  Email cannot be changed. Contact an admin if you need a transfer.
                </p>
              </div>

              {update.error && (
                <div className="flex items-start gap-2.5 px-3 py-2.5 rounded-lg bg-red-500/8 border border-red-500/20 text-sm text-red-400">
                  <AlertCircle className="size-4 shrink-0 mt-0.5" />
                  <span>{getApiErrorMessage(update.error)}</span>
                </div>
              )}

              {savedFlash && (
                <div className="flex items-center gap-2 text-sm text-emerald-400">
                  <CheckCircle2 className="size-4" />
                  Profile saved.
                </div>
              )}

              <div className="pt-2">
                <Button
                  onClick={() => update.mutate()}
                  disabled={!isDirty || update.isPending}
                  className="bg-blue-600 hover:bg-blue-500 text-white border-0 h-10 px-4 text-sm font-medium disabled:opacity-50"
                >
                  {update.isPending ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="size-4 animate-spin" />
                      Saving…
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5">
                      <UserIcon className="size-3.5" />
                      Save changes
                    </span>
                  )}
                </Button>
              </div>
            </div>
          </>
        )}
      </div>

      <span className="hidden">{user?.id}</span>
    </div>
  )
}