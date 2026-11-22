import { LogOut, RefreshCw } from 'lucide-react'
import { Button } from './ui'

export function Topbar({onRefresh,refreshing,user,onLogout}: {onRefresh:()=>void;refreshing:boolean;user?:{login:string;display_name:string}|null;onLogout?:()=>void}) {
  return <header className="flex min-h-[76px] items-center justify-between border-b border-line px-5 sm:px-8 lg:px-10"><div><h1 className="m-0 text-lg font-semibold text-white">Project match workspace</h1><p className="m-0 mt-1 text-xs text-slate-500">Discover collaborators across the 42 Network</p></div><div className="flex items-center gap-3">{user && <Button variant="outline" aria-label="Sign out" onClick={onLogout}><span className="hidden sm:inline">@{user.login}</span><LogOut size={15}/></Button>}<Button variant="outline" aria-label="Refresh projects" onClick={onRefresh} disabled={refreshing}><RefreshCw size={15} className={refreshing?'animate-spin':''}/><span className="hidden sm:inline">Refresh</span></Button></div></header>
}
