import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, AlertCircle, Upload, Mic } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { RiskBadge, ScoreBar } from '@/components/RiskBadge'
import { voiceService, type VoiceAnalysis } from '@/services/voice.service'
import { getApiErrorMessage } from '@/lib/errors'
import { formatRelativeTime } from '@/lib/format'

function VoiceResultCard({ result }: { result: VoiceAnalysis }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold mb-1.5">
            Deepfake probability
          </p>
          <div className="flex items-center gap-3">
            <span className="text-3xl font-bold text-white tabular-nums">
              {result.deepfake_probability.toFixed(0)}%
            </span>
            <span
              className={`text-xs font-semibold px-2 py-0.5 rounded-md border ${
                result.deepfake_probability >= 70
                  ? 'bg-red-500/15 text-red-400 border-red-500/30'
                  : result.deepfake_probability >= 40
                    ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                    : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
              }`}
            >
              {result.deepfake_probability >= 70
                ? 'LIKELY DEEPFAKE'
                : result.deepfake_probability >= 40
                  ? 'SUSPICIOUS'
                  : 'AUTHENTIC'}
            </span>
          </div>
        </div>
        <div>
          <p className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold mb-1.5">
            Risk score
          </p>
          <div className="flex items-center gap-3">
            <RiskBadge level={result.threat_level} />
            <ScoreBar score={result.risk_score} />
          </div>
        </div>
      </div>

      {result.flags.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1.5">
          {result.flags.map((flag) => (
            <span
              key={flag}
              className="text-[11px] px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20"
            >
              {flag}
            </span>
          ))}
        </div>
      )}

      <p className="text-sm text-slate-300 leading-relaxed mb-3">{result.reasoning}</p>

      <details className="group">
        <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-300 select-none">
          Show transcript
        </summary>
        <div className="mt-2 text-sm text-slate-400 italic bg-slate-950 rounded-md p-3 border border-slate-800 leading-relaxed">
          "{result.transcript}"
        </div>
      </details>
    </div>
  )
}

export default function DeepfakePage() {
  const qc = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [latestResult, setLatestResult] = useState<VoiceAnalysis | null>(null)

  const history = useQuery({
    queryKey: ['voice', 'history'],
    queryFn: () => voiceService.getHistory(1, 30),
  })

  const analyse = useMutation({
    mutationFn: () => {
      if (!selectedFile) throw new Error('Please select an audio file first')
      return voiceService.analyse(selectedFile)
    },
    onSuccess: (data) => {
      setLatestResult(data)
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      qc.invalidateQueries({ queryKey: ['voice', 'history'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  return (
    <div className="max-w-6xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-1">Deepfake Detection</h1>
        <p className="text-slate-500 text-sm">
          Upload a call recording. Whisper transcribes it, then GPT analyses for AI-generated voice
          and social-engineering patterns.
        </p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-8">
        <div className="flex items-center gap-2 mb-4">
          <Mic className="size-4 text-purple-400" />
          <h2 className="text-sm font-semibold text-white">Analyse audio file</h2>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="audio/webm,audio/wav,audio/mp3,audio/mpeg,.webm,.wav,.mp3"
          onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
          className="hidden"
        />

        <div
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-slate-700 hover:border-blue-500/50 rounded-xl p-8 text-center cursor-pointer transition-colors"
        >
          <Upload className="size-8 text-slate-500 mx-auto mb-3" />
          {selectedFile ? (
            <>
              <p className="text-sm text-white font-medium mb-1">{selectedFile.name}</p>
              <p className="text-xs text-slate-500">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB · click to change
              </p>
            </>
          ) : (
            <>
              <p className="text-sm text-slate-300 font-medium mb-1">Click to select audio</p>
              <p className="text-xs text-slate-500">webm, wav, mp3 — max 25MB</p>
            </>
          )}
        </div>

        {analyse.error && (
          <div className="mt-4 flex items-start gap-2.5 px-3.5 py-3 rounded-lg bg-red-500/8 border border-red-500/20 text-sm text-red-400">
            <AlertCircle className="size-4 shrink-0 mt-0.5" />
            <span>{getApiErrorMessage(analyse.error)}</span>
          </div>
        )}

        <Button
          onClick={() => analyse.mutate()}
          disabled={!selectedFile || analyse.isPending}
          className="mt-4 bg-purple-600 hover:bg-purple-500 text-white border-0 h-10 px-4 text-sm font-medium disabled:opacity-50"
        >
          {analyse.isPending ? (
            <span className="flex items-center gap-2">
              <Loader2 className="size-4 animate-spin" />
              Analysing… (this can take 30-60s)
            </span>
          ) : (
            <span className="flex items-center gap-1.5">
              <Mic className="size-3.5" />
              Analyse audio
            </span>
          )}
        </Button>

        {latestResult && (
          <div className="mt-5 pt-5 border-t border-slate-800">
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-3 font-semibold">
              Latest result
            </p>
            <VoiceResultCard result={latestResult} />
          </div>
        )}
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl">
        <div className="px-5 py-4 border-b border-slate-800">
          <h2 className="text-sm font-semibold text-white">Voice analysis history</h2>
        </div>

        {history.isLoading ? (
          <div className="flex items-center justify-center py-16 text-slate-500">
            <Loader2 className="size-4 animate-spin mr-2" />
            Loading…
          </div>
        ) : (history.data?.items.length ?? 0) === 0 ? (
          <div className="text-center py-16 text-slate-500 text-sm">
            No voice analyses yet. Upload a recording above to get started.
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {history.data?.items.map((item) => (
              <div key={item.id} className="px-5 py-3 hover:bg-slate-800/30 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <RiskBadge level={item.threat_level} />
                      <span className="text-xs font-mono text-slate-500">
                        Deepfake: {item.deepfake_probability.toFixed(0)}%
                      </span>
                      <span className="text-xs text-slate-600 ml-auto">
                        {formatRelativeTime(item.created_at)}
                      </span>
                    </div>
                    <p className="text-sm text-slate-400 italic line-clamp-1">
                      "{item.transcript_preview}"
                    </p>
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