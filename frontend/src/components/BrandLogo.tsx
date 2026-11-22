import { Flame } from 'lucide-react'

export function BrandLogo({ compact = false }: { compact?: boolean }) {
  return <div className="inline-flex items-center gap-2" aria-label="42 TeamFinder">
    <span className="font-display text-[1.7rem] font-black leading-none tracking-[-0.12em] text-white">42</span>
    <span className="h-8 w-[3px] -skew-x-12 rounded-full bg-brand-cyan shadow-[0_0_18px_rgba(0,215,215,.6)]" />
    {!compact && <span className="font-display text-xl font-extrabold italic tracking-[-0.04em] text-white">
      Team<span className="text-brand-pink">Finder</span>
    </span>}
    <Flame size={compact ? 17 : 20} className="-ml-1 text-brand-pink drop-shadow-[0_0_10px_rgba(255,59,124,.55)]" fill="currentColor" />
  </div>
}
