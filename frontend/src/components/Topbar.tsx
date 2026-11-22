import { LogOut, RefreshCw, Wifi } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import { Badge, Button, Skeleton } from './ui'

export function Topbar({lastSync,onRefresh,refreshing,user,onLogout}: {lastSync?:string;onRefresh:()=>void;refreshing:boolean;user?:{login:string;display_name:string}|null;onLogout?:()=>void}) {
  const health=useQuery({queryKey:['health'],queryFn:api.health,refetchInterval:30000})
  return <header className="flex min-h-[76px] items-center justify-between border-b border-line px-5 sm:px-8 lg:px-10"><div><h1 className="m-0 text-lg font-semibold text-white">Project match workspace</h1><p className="m-0 mt-1 text-xs text-slate-500">Discover collaborators across the 42 Network</p></div><div className="flex items-center gap-3">{health.isLoading?<Skeleton className="h-7 w-24"/>:<Badge tone={health.data?.status==='ok'?'green':'red'}><Wifi size={11} className="mr-1.5"/>{health.data?.api_mode==='demo'?'Demo data':'42 API connected'}</Badge>}<div className="hidden text-right sm:block"><div className="text-[10px] uppercase tracking-widest text-slate-600">Last sync</div><div className="text-xs text-slate-400">{lastSync?new Date(lastSync).toLocaleString():'Not scanned yet'}</div></div>{user && <Button variant="outline" aria-label="Sign out" onClick={onLogout}><span className="hidden sm:inline">@{user.login}</span><LogOut size={15}/></Button>}<Button variant="outline" aria-label="Refresh metadata" onClick={onRefresh} disabled={refreshing}><RefreshCw size={15} className={refreshing?'animate-spin':''}/><span className="hidden sm:inline">Refresh</span></Button></div></header>
}
