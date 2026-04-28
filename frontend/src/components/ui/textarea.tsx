import { cn } from '@/lib/utils'

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        'w-full bg-slate-900 border border-slate-700 text-white text-sm placeholder-slate-600 rounded-lg px-3 py-2.5 focus:outline-none focus:border-blue-500/60 focus:ring-2 focus:ring-blue-500/20 resize-none disabled:opacity-50 disabled:cursor-not-allowed',
        className,
      )}
      {...props}
    />
  )
}
