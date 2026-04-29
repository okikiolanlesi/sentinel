import { useRef, useState } from 'react'
import { Mic, Upload, AlertCircle, Clock, ChevronRight } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Dialog } from '@/components/ui/dialog'
import { useAnalyseVoice } from '@/features/deepfake/hooks/useAnalyseVoice'
import { useVoiceHistory } from '@/features/deepfake/hooks/useVoiceHistory'
import { useVoiceAnalysis } from '@/features/deepfake/hooks/useVoiceAnalysis'
import { getApiErrorMessage } from '@/lib/errors'
import type { VoiceAnalysis } from '@/features/deepfake/types'

const MAX_MB = 25
const ACCEPT = '.mp3,.wav,.webm,audio/mpeg,audio/wav,audio/webm'

function DeepfakeBar({ probability }: { probability: number }) {
  const color = probability >= 70 ? 'bg-red-500' : probability >= 40 ? 'bg-amber-500' : 'bg-emerald-500'
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-slate-500">
        <span>Deepfake probability</span>
        <span className="font-mono font-semibold text-white">{probability.toFixed(1)}%</span>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${probability}%` }} />
      </div>
    </div>
  )
}

function AnalysisCard({ analysis, onClose }: { analysis: VoiceAnalysis; onClose: () => void }) {
  return (
    <Dialog open onClose={onClose} title="Voice analysis detail" className="max-w-lg">
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Badge threat={analysis.threat_level}>{analysis.threat_level}</Badge>
          <span className={`text-xs font-semibold ${analysis.is_scam ? 'text-red-400' : 'text-emerald-400'}`}>
            {analysis.is_scam ? 'Scam detected' : 'No scam detected'}
          </span>
        </div>

        <DeepfakeBar probability={analysis.deepfake_probability} />

        <div>
          <p className="text-[11px] text-slate-500 mb-1.5 font-medium uppercase tracking-wide">Transcript</p>
          <p className="text-sm text-slate-300 leading-relaxed bg-slate-800/60 rounded-lg p-3 max-h-32 overflow-y-auto">{analysis.transcript}</p>
        </div>

        <div>
          <p className="text-[11px] text-slate-500 mb-1.5 font-medium uppercase tracking-wide">Reasoning</p>
          <p className="text-sm text-slate-300 leading-relaxed bg-slate-800/60 rounded-lg p-3">{analysis.reasoning}</p>
        </div>

        {analysis.flags.length > 0 && (
          <div>
            <p className="text-[11px] text-slate-500 mb-1.5 font-medium uppercase tracking-wide">Flags</p>
            <div className="flex flex-wrap gap-1.5">
              {analysis.flags.map((f) => (
                <span key={f} className="px-2 py-0.5 bg-slate-800 border border-slate-700 rounded text-xs text-slate-400 font-mono">{f}</span>
              ))}
            </div>
          </div>
        )}

        <p className="text-[11px] text-slate-600">{new Date(analysis.created_at).toLocaleString()}</p>
      </div>
    </Dialog>
  )
}

function HistoryDetail({ id, onClose }: { id: string; onClose: () => void }) {
  const { data, isLoading } = useVoiceAnalysis(id)
  if (isLoading || !data) return <Dialog open onClose={onClose}><span className="inline-block size-5 rounded-full border-2 border-slate-700 border-t-blue-400 animate-spin" /></Dialog>
  return <AnalysisCard analysis={data} onClose={onClose} />
}

export default function DeepfakePage() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [result, setResult] = useState<VoiceAnalysis | null>(null)

  const { mutate: analyse, isPending, error } = useAnalyseVoice()
  const { data: history, isLoading: historyLoading } = useVoiceHistory()

  function handleFile(file: File) {
    if (file.size > MAX_MB * 1024 * 1024) return
    analyse(file, { onSuccess: setResult })
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <div className="space-y-7">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-slate-800 border border-slate-700">
          <Mic className="size-4 text-slate-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Deepfake Detection</h1>
          <p className="text-slate-500 text-xs mt-0.5">Upload audio for AI-powered analysis. Supports MP3, WAV, WebM up to 25 MB.</p>
        </div>
      </div>

      {/* Upload zone */}
      <div
        className={`relative border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer ${
          dragging ? 'border-blue-500/60 bg-blue-500/5' : 'border-slate-700 hover:border-slate-600 bg-slate-900/40'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); e.target.value = '' }}
        />
        {isPending ? (
          <div className="flex flex-col items-center gap-3">
            <span className="size-8 rounded-full border-2 border-slate-700 border-t-blue-400 animate-spin" />
            <p className="text-sm text-slate-400">Analysing audio…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="p-3 rounded-full bg-slate-800 border border-slate-700">
              <Upload className="size-5 text-slate-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-300">Drop audio file here or click to browse</p>
              <p className="text-xs text-slate-500 mt-1">MP3, WAV, WebM · Max {MAX_MB} MB</p>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-2.5 px-4 py-3 rounded-lg bg-red-500/8 border border-red-500/20 text-sm text-red-400">
          <AlertCircle className="size-4 shrink-0 mt-0.5" />
          {getApiErrorMessage(error)}
        </div>
      )}

      {/* Inline result */}
      {result && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Badge threat={result.threat_level}>{result.threat_level}</Badge>
              <span className={`text-sm font-semibold ${result.is_scam ? 'text-red-400' : 'text-emerald-400'}`}>
                {result.is_scam ? 'Scam detected' : 'Legitimate'}
              </span>
            </div>
            <button onClick={() => setResult(null)} className="text-xs text-slate-600 hover:text-slate-400 transition-colors">Dismiss</button>
          </div>

          <DeepfakeBar probability={result.deepfake_probability} />

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-800/60 rounded-lg p-3">
              <p className="text-[11px] text-slate-500 mb-1">Risk score</p>
              <p className="text-lg font-bold text-white">{result.risk_score.toFixed(1)}<span className="text-xs text-slate-500">/100</span></p>
            </div>
            <div className="bg-slate-800/60 rounded-lg p-3">
              <p className="text-[11px] text-slate-500 mb-1">Action</p>
              <p className={`text-lg font-bold ${result.threat_level === 'HIGH' ? 'text-red-400' : result.threat_level === 'MEDIUM' ? 'text-amber-400' : 'text-emerald-400'}`}>
                {result.threat_level === 'HIGH' ? 'BLOCK' : result.threat_level === 'MEDIUM' ? 'REVIEW' : 'ALLOW'}
              </p>
            </div>
          </div>

          <div>
            <p className="text-[11px] text-slate-500 mb-1.5 font-medium uppercase tracking-wide">Transcript</p>
            <p className="text-sm text-slate-300 leading-relaxed bg-slate-800/40 rounded-lg p-3 max-h-24 overflow-y-auto">{result.transcript}</p>
          </div>

          <p className="text-sm text-slate-400 leading-relaxed">{result.reasoning}</p>

          {result.flags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {result.flags.map((f) => (
                <span key={f} className="px-2 py-0.5 bg-slate-800 border border-slate-700 rounded text-xs text-slate-400 font-mono">{f}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* History */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-800">
          <Clock className="size-4 text-slate-500" />
          <p className="text-sm font-medium text-slate-300">Analysis history</p>
          {history && <span className="text-xs text-slate-600">({history.total})</span>}
        </div>

        {historyLoading && (
          <div className="py-10 text-center"><span className="inline-block size-5 rounded-full border-2 border-slate-700 border-t-blue-400 animate-spin" /></div>
        )}
        {!historyLoading && history?.items.length === 0 && (
          <p className="px-5 py-10 text-center text-slate-500 text-sm">No analyses yet.</p>
        )}

        <div className="divide-y divide-slate-800/60">
          {history?.items.map((item) => (
            <button
              key={item.id}
              onClick={() => setSelectedId(item.id)}
              className="w-full flex items-center gap-4 px-5 py-3.5 hover:bg-slate-800/20 transition-colors text-left"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-300 truncate">{item.transcript_preview}</p>
                <p className="text-[11px] text-slate-600 mt-0.5">{new Date(item.created_at).toLocaleString()}</p>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-xs font-mono text-slate-500">{item.deepfake_probability.toFixed(0)}%</span>
                <Badge threat={item.threat_level}>{item.threat_level}</Badge>
                <ChevronRight className="size-3.5 text-slate-600" />
              </div>
            </button>
          ))}
        </div>
      </div>

      {selectedId && <HistoryDetail id={selectedId} onClose={() => setSelectedId(null)} />}
    </div>
  )
}
