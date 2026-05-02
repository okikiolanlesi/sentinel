import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Loader2, AlertCircle, Key, Copy, RefreshCw, Eye, EyeOff, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { usersService } from '@/services/users.service'
import { getApiErrorMessage } from '@/lib/errors'

export default function ApiKeysPage() {
  const [revealedKey, setRevealedKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [showKey, setShowKey] = useState(true)
  const [confirmRotate, setConfirmRotate] = useState(false)

  const generate = useMutation({
    mutationFn: () => usersService.regenerateApiKey(),
    onSuccess: (data) => {
      setRevealedKey(data.api_key)
      setShowKey(true)
      setConfirmRotate(false)
    },
  })

  function copyKey() {
    if (!revealedKey) return
    navigator.clipboard.writeText(revealedKey).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const masked = revealedKey
    ? showKey
      ? revealedKey
      : revealedKey.slice(0, 12) + '•'.repeat(20) + revealedKey.slice(-4)
    : null

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-1">API Keys</h1>
        <p className="text-slate-500 text-sm">
          Generate keys for external integrations. Use the <code className="text-blue-400">X-API-Key</code> header
          on calls to <code className="text-blue-400">/api/scan/api</code>.
        </p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Key className="size-4 text-amber-400" />
          <h2 className="text-sm font-semibold text-white">Your API key</h2>
        </div>

        {!revealedKey ? (
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-5 text-center">
            <p className="text-sm text-slate-400 mb-4">
              Click below to generate (or rotate) your API key. The key is shown <strong className="text-white">once only</strong> — copy it immediately.
            </p>
            {!confirmRotate ? (
              <Button
                onClick={() => setConfirmRotate(true)}
                className="bg-amber-600 hover:bg-amber-500 text-white border-0 h-10 px-4 text-sm font-medium"
              >
                <RefreshCw className="size-3.5 mr-1.5" />
                Generate / rotate API key
              </Button>
            ) : (
              <div className="space-y-3">
                <div className="flex items-start gap-2 text-sm text-amber-400 text-left bg-amber-500/8 border border-amber-500/20 rounded-lg p-3">
                  <AlertTriangle className="size-4 shrink-0 mt-0.5" />
                  <span>
                    Generating a new key will invalidate any existing key currently in use. All clients
                    using the old key will start receiving 401 errors.
                  </span>
                </div>
                <div className="flex justify-center gap-2">
                  <Button
                    onClick={() => setConfirmRotate(false)}
                    className="bg-slate-800 hover:bg-slate-700 text-white border-0 h-9 px-3 text-sm"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={() => generate.mutate()}
                    disabled={generate.isPending}
                    className="bg-amber-600 hover:bg-amber-500 text-white border-0 h-9 px-3 text-sm disabled:opacity-50"
                  >
                    {generate.isPending ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="size-4 animate-spin" />
                        Generating…
                      </span>
                    ) : (
                      'Yes, rotate it'
                    )}
                  </Button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <>
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
              <div className="flex items-center gap-2">
                <code className="flex-1 text-sm text-emerald-400 font-mono break-all">{masked}</code>
                <button
                  onClick={() => setShowKey((v) => !v)}
                  className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                  aria-label={showKey ? 'Hide key' : 'Show key'}
                >
                  {showKey ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                </button>
                <button
                  onClick={copyKey}
                  className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                  aria-label="Copy"
                >
                  <Copy className="size-3.5" />
                </button>
              </div>
            </div>
            {copied && (
              <p className="text-xs text-emerald-400 mt-2">Copied to clipboard.</p>
            )}
            <div className="mt-4 flex items-start gap-2 text-sm text-amber-400 bg-amber-500/8 border border-amber-500/20 rounded-lg p-3">
              <AlertTriangle className="size-4 shrink-0 mt-0.5" />
              <span>
                Save this key now — once you leave this page, you'll have to rotate it to see it again.
              </span>
            </div>
            <Button
              onClick={() => {
                setRevealedKey(null)
                setConfirmRotate(false)
              }}
              className="mt-4 bg-slate-800 hover:bg-slate-700 text-white border-0 h-9 px-3 text-sm"
            >
              I've saved it
            </Button>
          </>
        )}

        {generate.error && (
          <div className="mt-4 flex items-start gap-2.5 px-3.5 py-3 rounded-lg bg-red-500/8 border border-red-500/20 text-sm text-red-400">
            <AlertCircle className="size-4 shrink-0 mt-0.5" />
            <span>{getApiErrorMessage(generate.error)}</span>
          </div>
        )}
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h2 className="text-sm font-semibold text-white mb-3">Integration example</h2>
        <p className="text-xs text-slate-500 mb-3">
          Send a message to SentinelAI for live fraud scoring. Returns risk_score, threat_level, action, flags.
        </p>
        <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 overflow-x-auto">
          <pre className="text-xs text-slate-300 font-mono leading-relaxed">
{`curl -X POST $SENTINEL_BACKEND/api/scan/api \\
  -H "X-API-Key: <your-api-key>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "content": "URGENT: Verify your BVN at gtb-verify.com",
    "message_type": "sms",
    "sender": "+2348030001234"
  }'`}
          </pre>
        </div>
      </div>
    </div>
  )
}