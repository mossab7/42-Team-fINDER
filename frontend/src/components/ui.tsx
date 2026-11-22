import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from 'react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

// eslint-disable-next-line react-refresh/only-export-components
export function cn(...values: (string | false | null | undefined)[]) { return twMerge(clsx(values)) }
export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) { return <div className={cn('rounded-2xl border border-line bg-panel/80 shadow-sm backdrop-blur', className)} {...props}/> }
export function Button({ className, variant='primary', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & {variant?:'primary'|'outline'|'ghost'}) { return <button className={cn('inline-flex h-10 items-center justify-center gap-2 rounded-lg px-4 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-accent/50', variant==='primary'&&'bg-accent text-[#07110d] hover:bg-[#5ae9b5] shadow-glow', variant==='outline'&&'border border-line bg-white/[.03] text-slate-200 hover:border-slate-500 hover:bg-white/[.06]', variant==='ghost'&&'text-slate-400 hover:bg-white/[.05] hover:text-white', className)} {...props}/> }
export function Badge({ children, tone='neutral' }: {children:ReactNode;tone?:'green'|'amber'|'red'|'blue'|'neutral'}) { return <span className={cn('inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold', tone==='green'&&'border-emerald-400/20 bg-emerald-400/10 text-emerald-300', tone==='amber'&&'border-amber-400/20 bg-amber-400/10 text-amber-300', tone==='red'&&'border-red-400/20 bg-red-400/10 text-red-300', tone==='blue'&&'border-cyan-400/20 bg-cyan-400/10 text-cyan-300', tone==='neutral'&&'border-slate-500/20 bg-slate-400/10 text-slate-300')}>{children}</span> }
export function Skeleton({className}: {className?:string}) { return <div className={cn('animate-pulse rounded-lg bg-white/[.07]', className)}/> }
