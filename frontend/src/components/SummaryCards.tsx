import { CircleDot, ShieldCheck, UserCheck, Users, UsersRound } from 'lucide-react'
import type { ScanSummary } from '../types/api'
import { Card, Skeleton } from './ui'

export function SummaryCards({summary,loading,solo=false}: {summary?:ScanSummary;loading:boolean;solo?:boolean}) {
 const cards=solo
  ? [['Eligible students',summary?.total_eligible_students,Users],['Working on project',summary?.students_working_on_project,UserCheck],['Black-hole exclusions',summary?.excluded_blackholed_students,ShieldCheck],['Team matching','Solo',CircleDot]] as const
  : [['Eligible students',summary?.total_eligible_students,Users],['Without active teams',summary?.students_without_active_teams,UserCheck],['Teams below limit',summary?.teams_below_size_limit,UsersRound],['Potential spots',summary?.potentially_available_spots,CircleDot]] as const
 return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{cards.map(([label,value,Icon])=><Card key={label} className="relative overflow-hidden p-4"><div className="absolute -right-6 -top-7 h-20 w-20 rounded-full bg-accent/[.04]"/><div className="flex items-start justify-between"><div><div className="text-xs font-medium text-slate-500">{label}</div>{loading?<Skeleton className="mt-3 h-8 w-16"/>:<div className="mt-2 text-2xl font-bold tracking-tight text-white">{value??'—'}</div>}</div><div className="rounded-lg border border-accent/10 bg-accent/[.07] p-2 text-accent"><Icon size={17}/></div></div>{label==='Potential spots'&&<div className="mt-2 text-[10px] text-slate-600">Capacity estimate, not confirmed joinability</div>}</Card>)}</div>
}
