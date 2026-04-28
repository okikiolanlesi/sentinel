import { useState } from 'react'
import { Key, Copy, Check, AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { useGenerateApiKey } from '@/features/auth/hooks/useGenerateApiKey'
import { getApiErrorMessage } from '@/lib/errors'

export default function ApiKeysPage() {
  const { mutate, isPending, error } = useGenerateApiKey()
  const [generatedKey, setGeneratedKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  function handleGenerate() {
    mutate(undefined, {
      onSuccess: (data) => setGeneratedKey(data.api_key),
    })
  }

  function handleCopy() {
    if (!generatedKey) return
    navigator.clipboard.writeText(generatedKey).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="max-w-lg">
      <div className="flex items-center gap-3 mb-7">
        <div className="p-2 rounded-lg bg-slate-800 border border-slate-700">
          <Key className="size-4 text-slate-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">API Keys</h1>
          <p className="text-slate-500 text-xs mt-0.5">Manage keys for external integrations.</p>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-5">
        <div className="p-4 rounded-lg bg-amber-500/6 border border-amber-500/20">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="size-4 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs text-amber-400/90 leading-relaxed">
              Generating a new key immediately invalidates your existing key. All integrations using the old key will stop working.
            </div>
          </div>
        </div>

        <div>
          <p className="text-sm text-slate-400 mb-1.5">Your API key</p>
          <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-3 h-10">
            <Key className="size-3.5 text-slate-600 shrink-0" />
            <span className="text-sm text-slate-500 font-mono tracking-widest flex-1">sk-sentinel-••••••••••••••••••••••••••••••••</span>
          </div>
          <p className="text-[11px] text-slate-600 mt-1.5">The full key is only visible once when generated.</p>
        </div>

        {error && (
          <p className="text-sm text-red-400">{getApiErrorMessage(error)}</p>
        )}

        <Button
          onClick={handleGenerate}
          disabled={isPending}
          className="bg-blue-600 hover:bg-blue-500 text-white border-0 h-10 px-5 text-sm font-medium disabled:opacity-60"
        >
          {isPending ? (
            <span className="flex items-center gap-2">
              <span className="size-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              Generating…
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <RefreshCw className="size-3.5" />
              Generate new key
            </span>
          )}
        </Button>
      </div>

      <Dialog
        open={!!generatedKey}
        onClose={() => setGeneratedKey(null)}
        title="Your new API key"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-amber-500/6 border border-amber-500/20 flex items-start gap-2">
            <AlertTriangle className="size-4 text-amber-400 shrink-0 mt-0.5" />
            <p className="text-xs text-amber-400/90 leading-relaxed">
              Copy this key now. It will <strong>not</strong> be shown again.
            </p>
          </div>

          <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5">
            <code className="text-xs text-emerald-400 font-mono flex-1 break-all">{generatedKey}</code>
            <button
              onClick={handleCopy}
              className="shrink-0 text-slate-500 hover:text-slate-300 transition-colors p-1"
              aria-label="Copy key"
            >
              {copied ? <Check className="size-3.5 text-emerald-400" /> : <Copy className="size-3.5" />}
            </button>
          </div>

          <Button
            onClick={() => setGeneratedKey(null)}
            className="w-full bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 h-9 text-sm"
          >
            Done
          </Button>
        </div>
      </Dialog>
    </div>
  )
}
