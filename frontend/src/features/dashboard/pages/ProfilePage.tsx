import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { AlertCircle, CheckCircle2, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from '@/components/ui/form'
import { useProfile } from '@/features/users/hooks/useProfile'
import { useUpdateProfile } from '@/features/users/hooks/useUpdateProfile'
import { getApiErrorMessage } from '@/lib/errors'

const schema = z.object({
  full_name:    z.string().trim().min(1, 'Name is required'),
  organisation: z.string().trim().min(1, 'Organisation is required'),
})
type FormData = z.infer<typeof schema>

export default function ProfilePage() {
  const { data: profile, isLoading } = useProfile()
  const { mutate, isPending, isSuccess, error, reset } = useUpdateProfile()

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: '', organisation: '' },
    mode: 'onChange',
  })

  useEffect(() => {
    if (profile) {
      form.reset({ full_name: profile.full_name ?? '', organisation: profile.organisation ?? '' })
    }
  }, [profile, form])

  function onSubmit(data: FormData) {
    reset()
    mutate(data)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <span className="size-5 rounded-full border-2 border-slate-700 border-t-blue-400 animate-spin" />
      </div>
    )
  }

  return (
    <div className="max-w-lg">
      <div className="flex items-center gap-3 mb-7">
        <div className="p-2 rounded-lg bg-slate-800 border border-slate-700">
          <User className="size-4 text-slate-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Profile</h1>
          <p className="text-slate-500 text-xs mt-0.5">Update your personal details.</p>
        </div>
      </div>

      {isSuccess && (
        <div className="mb-5 flex items-center gap-2.5 px-3.5 py-3 rounded-lg bg-emerald-500/8 border border-emerald-500/20 text-sm text-emerald-400">
          <CheckCircle2 className="size-4 shrink-0" />
          Profile updated successfully.
        </div>
      )}
      {error && (
        <div className="mb-5 flex items-start gap-2.5 px-3.5 py-3 rounded-lg bg-red-500/8 border border-red-500/20 text-sm text-red-400">
          <AlertCircle className="size-4 shrink-0 mt-0.5" />
          {getApiErrorMessage(error)}
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-4 mb-6 pb-5 border-b border-slate-800">
          <div className="size-12 rounded-full bg-linear-to-br from-blue-500 to-purple-500 flex items-center justify-center text-base font-bold text-white shrink-0">
            {profile?.full_name ? profile.full_name.slice(0, 2).toUpperCase() : '?'}
          </div>
          <div>
            <div className="text-sm font-semibold text-white">{profile?.full_name || '—'}</div>
            <div className="text-xs text-slate-500">{profile?.email}</div>
            <div className="text-[11px] text-slate-600 mt-0.5 capitalize">{profile?.role} · {profile?.organisation}</div>
          </div>
        </div>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-4">
            <FormField
              control={form.control}
              name="full_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-slate-300 text-sm">Full name</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Ada Okafor"
                      className="bg-slate-800 border-slate-700 text-white placeholder-slate-600 focus-visible:border-blue-500/60 focus-visible:ring-blue-500/20 h-10"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="organisation"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-slate-300 text-sm">Organisation</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Acme Telecom Ltd"
                      className="bg-slate-800 border-slate-700 text-white placeholder-slate-600 focus-visible:border-blue-500/60 focus-visible:ring-blue-500/20 h-10"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="pt-1">
              <Button
                type="submit"
                disabled={isPending || !form.formState.isDirty}
                className="bg-blue-600 hover:bg-blue-500 text-white border-0 h-10 px-5 text-sm font-medium disabled:opacity-60"
              >
                {isPending ? (
                  <span className="flex items-center gap-2">
                    <span className="size-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    Saving…
                  </span>
                ) : 'Save changes'}
              </Button>
            </div>
          </form>
        </Form>
      </div>
    </div>
  )
}
