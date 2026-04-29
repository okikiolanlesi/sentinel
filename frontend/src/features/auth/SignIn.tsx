import { Link, useNavigate } from "react-router-dom";
import { zodResolver } from "@hookform/resolvers/zod";
import { Shield, AlertCircle, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { PasswordInput } from "@/components/PasswordInput";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";
import { useSignIn } from "./hooks/useSignIn";
import { AUTH_ROUTES, MOCK_CREDENTIALS } from "./constants";
import { signInSchema, type SignInFormData } from "./schemas";
import { getApiErrorMessage } from "@/lib/errors";
import { useForm } from "react-hook-form";

const brandStats = [
  { value: "99.2%", label: "Detection accuracy" },
  { value: "<50ms", label: "Average response time" },
  { value: "500K+", label: "Threats blocked" },
];

export default function SignIn() {
  const navigate = useNavigate();
  const { mutate, isPending, error } = useSignIn();

  const form = useForm<SignInFormData>({
    resolver: zodResolver(signInSchema),
    defaultValues: { email: "", password: "", rememberMe: false },
    mode: "onChange",
  });

  function onSubmit(data: SignInFormData) {
    mutate(data, { onSuccess: () => navigate(AUTH_ROUTES.DASHBOARD) });
  }

  const serverError = error ? getApiErrorMessage(error) : null;

  return (
    <div className="min-h-screen bg-slate-950 flex">
      {/* Left branding panel */}
      <div className="hidden lg:flex lg:w-[45%] flex-col justify-between p-10 bg-slate-900 border-r border-slate-800 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_0%_100%,rgba(59,130,246,0.08),transparent)] pointer-events-none" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(30,41,59,0.15)_1px,transparent_1px),linear-gradient(to_bottom,rgba(30,41,59,0.15)_1px,transparent_1px)] bg-size-[3rem_3rem] pointer-events-none" />

        <div className="relative flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-blue-500/15 border border-blue-500/25">
            <Shield className="size-4 text-blue-400" />
          </div>
          <span className="font-bold text-white tracking-widest text-sm">
            SENTINEL
          </span>
        </div>

        <div className="relative space-y-8">
          <div>
            <h2 className="text-3xl font-bold text-white leading-tight mb-3">
              Telecom fraud intelligence,{" "}
              <span className="bg-linear-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                in real time
              </span>
            </h2>
            <p className="text-slate-500 text-sm leading-relaxed">
              AI-powered scam detection, deepfake voice analysis, and risk
              scoring for telecom operators and financial institutions.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-4">
            {brandStats.map((s) => (
              <div
                key={s.label}
                className="bg-slate-800/60 rounded-xl p-4 border border-slate-700/50"
              >
                <div className="text-2xl font-bold text-white mb-1">
                  {s.value}
                </div>
                <div className="text-xs text-slate-500">{s.label}</div>
              </div>
            ))}
          </div>

          <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs font-medium text-slate-300">
                  Live Threat Monitor
                </span>
              </div>
              <span className="text-xs text-slate-500 font-mono">
                4,271 blocked today
              </span>
            </div>
            {[
              {
                channel: "SMS",
                risk: 87,
                verdict: "BLOCKED",
                verdictColor: "text-red-400",
              },
              {
                channel: "Voice",
                risk: 82,
                verdict: "FLAGGED",
                verdictColor: "text-amber-400",
              },
            ].map((item) => (
              <div key={item.channel} className="flex items-center gap-2">
                <span className="text-[10px] font-semibold bg-slate-700 px-1.5 py-0.5 rounded text-slate-300 shrink-0">
                  {item.channel}
                </span>
                <div className="flex-1 h-1 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-red-500 rounded-full"
                    style={{ width: `${item.risk}%` }}
                  />
                </div>
                <span className="text-[10px] text-slate-500 font-mono">
                  {item.risk}/100
                </span>
                <span className={`text-[10px] font-bold ${item.verdictColor}`}>
                  {item.verdict}
                </span>
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-slate-600">
          © {new Date().getFullYear()} Sentinel AI. Enterprise fraud
          intelligence.
        </p>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center px-4 sm:px-8 py-12">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="p-1.5 rounded-lg bg-blue-500/15 border border-blue-500/25">
              <Shield className="size-4 text-blue-400" />
            </div>
            <span className="font-bold text-white tracking-widest text-sm">
              SENTINEL
            </span>
          </div>

          <div className="mb-8">
            <h1 className="text-2xl font-bold text-white mb-1.5">
              Welcome back
            </h1>
            <p className="text-slate-500 text-sm">
              Sign in to your Sentinel account to continue.
            </p>
          </div>

          {serverError && (
            <div className="mb-5 flex items-start gap-2.5 px-3.5 py-3 rounded-lg bg-red-500/8 border border-red-500/20 text-sm text-red-400">
              <AlertCircle className="size-4 shrink-0 mt-0.5" />
              {serverError}
            </div>
          )}

          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              noValidate
              className="space-y-5"
            >
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-slate-300 text-sm">
                      Email address
                    </FormLabel>
                    <FormControl>
                      <Input
                        type="email"
                        autoComplete="email"
                        placeholder="you@company.com"
                        className="bg-slate-900 border-slate-700 text-white placeholder-slate-600 focus-visible:border-blue-500/60 focus-visible:ring-blue-500/20 h-10"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-slate-300 text-sm">
                      Password
                    </FormLabel>
                    <FormControl>
                      <PasswordInput
                        autoComplete="current-password"
                        placeholder="••••••••"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex items-center justify-between">
                <FormField
                  control={form.control}
                  name="rememberMe"
                  render={({ field }) => (
                    <Checkbox
                      id="rememberMe"
                      label="Remember me"
                      checked={field.value}
                      onChange={field.onChange}
                    />
                  )}
                />
                <a
                  href="#"
                  className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
                >
                  Forgot password?
                </a>
              </div>

              <Button
                type="submit"
                disabled={isPending}
                className="w-full bg-blue-600 hover:bg-blue-500 text-white border-0 h-10 text-sm font-medium shadow-lg shadow-blue-500/20 disabled:opacity-60"
              >
                {isPending ? (
                  <span className="flex items-center gap-2">
                    <span className="size-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    Signing in…
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5">
                    Sign in <ArrowRight className="size-4" />
                  </span>
                )}
              </Button>
            </form>
          </Form>

          <p className="mt-6 text-center text-sm text-slate-500">
            Don't have an account?{" "}
            <Link
              to={AUTH_ROUTES.SIGN_UP}
              className="text-blue-400 hover:text-blue-300 font-medium transition-colors"
            >
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
