import { ArrowRight, Play, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

const threats = [
  {
    id: 1,
    channel: "SMS",
    channelColor: "bg-blue-500/15 text-blue-400",
    identifier: "+234-701-234-5678",
    content: "Win free airtime! Click bit.ly/claim-now to redeem...",
    score: 87,
    barColor: "bg-red-500",
    action: "BLOCKED",
    actionColor: "bg-red-500/15 text-red-400",
  },
  {
    id: 2,
    channel: "WhatsApp",
    channelColor: "bg-emerald-500/15 text-emerald-400",
    identifier: "+1-555-987-6543",
    content: "Your bank account has been suspended. Verify now...",
    score: 95,
    barColor: "bg-red-500",
    action: "BLOCKED",
    actionColor: "bg-red-500/15 text-red-400",
  },
  {
    id: 3,
    channel: "Voice",
    channelColor: "bg-purple-500/15 text-purple-400",
    identifier: "+44-7700-900123",
    content: "Deepfake audio pattern detected — 94% confidence",
    score: 82,
    barColor: "bg-amber-500",
    action: "FLAGGED",
    actionColor: "bg-amber-500/15 text-amber-400",
  },
];

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center overflow-hidden bg-slate-950">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,rgba(59,130,246,0.12),transparent)]" />
        <div className="absolute top-1/4 left-1/6 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
        <div className="absolute top-1/3 right-1/6 w-80 h-80 bg-purple-500/5 rounded-full blur-3xl" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(30,41,59,0.15)_1px,transparent_1px),linear-gradient(to_bottom,rgba(30,41,59,0.15)_1px,transparent_1px)] bg-[size:4rem_4rem]" />
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16 grid lg:grid-cols-2 gap-16 items-center w-full">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-medium mb-6">
            <span className="size-1.5 rounded-full bg-blue-400 animate-pulse" />
            AI-Powered Telecom Fraud Intelligence
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold leading-[1.1] text-white mb-6 tracking-tight">
            Stop Telecom Fraud{" "}
            <span className="bg-gradient-to-r from-blue-400 via-cyan-400 to-purple-400 bg-clip-text text-transparent">
              Before It Strikes
            </span>
          </h1>

          <p className="text-lg text-slate-400 leading-relaxed mb-8 max-w-lg">
            Sentinel uses large language models and AI signal analysis to detect
            scam messages, deepfake voice calls, and social engineering attacks
            in real time — protecting your customers before threats reach them.
          </p>

          <div className="flex flex-wrap gap-3 mb-10">
            <Button
              variant="outline"
              className="border-slate-700 bg-slate-900/50 text-slate-300 hover:bg-slate-800 hover:text-white h-11 px-6 text-sm gap-2"
            >
              <Play className="size-3.5 fill-current" />
              Watch Demo
            </Button>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-sm text-slate-500">
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="size-4 text-emerald-500" />
              No credit card required
            </div>
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="size-4 text-emerald-500" />
              5-minute API integration
            </div>
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="size-4 text-emerald-500" />
              Enterprise-grade security
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
