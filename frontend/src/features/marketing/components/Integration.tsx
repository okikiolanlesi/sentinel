import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";

const codeSnippet = `POST https://api.sentinel.ai/v1/scan

{
  "channel": "sms",
  "sender": "+234-701-234-5678",
  "content": "Congrats! You have won ₦500,000.
              Click http://bit.ly/claim to collect.",
  "recipient": "+234-802-987-6543"
}

// Response — 47ms
{
  "risk_score": 91,
  "verdict": "BLOCK",
  "reasons": [
    "suspicious_url_detected",
    "prize_lure_pattern",
    "high_velocity_sender"
  ],
  "confidence": 0.97
}`;

const benefits = [
  "REST API with JSON — any language, any stack",
  "Sub-50ms response for real-time decisioning",
  "Webhooks for async bulk processing",
  "Full SDK support and comprehensive docs",
  "Role-based API key management",
];

export default function Integration() {
  return (
    <section id="integration" className="py-24 bg-slate-900/40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-400 text-xs font-medium mb-6">
              API-First Design
            </div>
            <h2 className="text-4xl font-bold text-white mb-5 tracking-tight">
              Integrate in{" "}
              <span className="bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">
                one API call
              </span>
            </h2>
            <p className="text-slate-400 text-lg leading-relaxed mb-8">
              Sentinel is built API-first. Send us a communication, get back a
              risk score and action in milliseconds. No complex setup, no model
              training, no infrastructure to manage.
            </p>
          </div>

          <div className="relative">
            <div className="absolute -inset-2 bg-amber-500/5 rounded-3xl blur-xl" />
            <div className="relative bg-slate-950 border border-slate-700/50 rounded-2xl overflow-hidden shadow-2xl shadow-black/50">
              <div className="flex items-center gap-2 px-4 py-3 bg-slate-800/60 border-b border-slate-700/50">
                <span className="size-2.5 rounded-full bg-red-500/60" />
                <span className="size-2.5 rounded-full bg-amber-500/60" />
                <span className="size-2.5 rounded-full bg-emerald-500/60" />
                <span className="ml-3 text-xs text-slate-500 font-mono">
                  sentinel-api.sh
                </span>
              </div>
              <pre className="p-5 text-xs leading-relaxed overflow-x-auto">
                <code className="text-slate-300 font-mono whitespace-pre">
                  {codeSnippet}
                </code>
              </pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
