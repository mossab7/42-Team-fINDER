import { useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Compass, Heart, LoaderCircle, Search, ShieldCheck, Sparkles } from 'lucide-react'
import { Layout } from './components/Layout'
import { Topbar } from './components/Topbar'
import { BrandLogo } from './components/BrandLogo'
import { Dashboard } from './pages/Dashboard'
import { Discover, Matches } from './pages/Matchmaking'
import { api } from './services/api'

function LoginGate({ reason }: { reason?: string }) {
  return <main className="relative min-h-screen overflow-hidden bg-ink px-5 py-8 text-slate-100 sm:px-8">
    <div className="brand-orb -left-36 -top-40 h-[30rem] w-[30rem] bg-brand-cyan" />
    <div className="brand-orb -right-40 top-8 h-[34rem] w-[34rem] bg-brand-pink" />
    <div className="relative mx-auto flex min-h-[calc(100vh-4rem)] max-w-7xl flex-col">
      <header className="flex items-center justify-between"><BrandLogo /><span className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/[.035] px-3 py-1.5 text-xs text-slate-400 sm:inline-flex"><ShieldCheck size={13} className="text-brand-cyan" />42 students only</span></header>
      <section className="grid flex-1 items-center gap-8 py-10 lg:grid-cols-[.92fr_1.08fr] lg:py-14">
        <div className="relative z-10 max-w-xl">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-brand-pink/20 bg-brand-pink/[.07] px-3 py-1.5 text-xs font-semibold text-pink-200"><Sparkles size={14} className="text-brand-pink" />Built for the 42 Network</div>
          <h1 className="m-0 font-display text-5xl font-black leading-[.98] tracking-[-.055em] text-white sm:text-6xl xl:text-7xl">Find your next<br />project <span className="text-brand-pink">teammate.</span></h1>
          <p className="mt-6 max-w-lg text-base leading-7 text-slate-400 sm:text-lg">Swipe through verified peers, match around the projects you share, and explore open teams across your campus.</p>
          {reason && <p className="mt-5 rounded-xl border border-rose-400/20 bg-rose-500/10 p-3 text-sm text-rose-200">Sign-in did not complete. Please try again.</p>}
          <a href={api.loginUrl()} className="mt-8 inline-flex min-h-14 w-full items-center justify-center gap-2 rounded-xl bg-brand-cyan px-6 py-3.5 font-bold text-[#041316] shadow-[0_0_35px_rgba(0,215,215,.24)] transition hover:-translate-y-0.5 hover:bg-[#35ebeb] hover:shadow-[0_0_45px_rgba(0,215,215,.34)] focus:outline-none focus:ring-2 focus:ring-brand-cyan focus:ring-offset-2 focus:ring-offset-ink sm:w-auto"><ShieldCheck size={19} />Continue with 42</a>
          <p className="mt-4 text-xs text-slate-600">Your identity and active projects are verified securely through 42 Intra.</p>
        </div>
        <div className="relative mx-auto w-full max-w-2xl lg:max-w-none"><div className="absolute inset-x-[15%] bottom-[8%] h-24 rounded-full bg-brand-pink/20 blur-3xl" /><img src="/assets/team-cards-hero.webp" alt="Two glowing project teammate cards" className="brand-float relative mx-auto w-full max-w-[680px] drop-shadow-[0_35px_70px_rgba(0,0,0,.5)]" /></div>
      </section>
    </div>
  </main>
}

const links = [['/discover', 'Discover', Compass, 'cyan'], ['/matches', 'Matches', Heart, 'pink'], ['/explore', 'Explore', Search, 'cyan']] as const

function Navigation() {
  return <nav aria-label="Main navigation" className="sticky top-0 z-20 border-b border-line/80 bg-[#070b12]/90 px-4 backdrop-blur-xl sm:px-8"><div className="mx-auto flex max-w-7xl gap-1 overflow-x-auto py-2">{links.map(([to, label, Icon, tone]) => <NavLink key={to} to={to} className={({ isActive }) => `relative inline-flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition ${isActive ? tone === 'pink' ? 'bg-brand-pink/10 text-pink-200' : 'bg-brand-cyan/10 text-cyan-100' : 'text-slate-500 hover:bg-white/[.04] hover:text-white'}`}>{({ isActive }) => <><Icon size={16} fill={label === 'Matches' && isActive ? 'currentColor' : 'none'} />{label}{isActive && <span className={`absolute inset-x-4 -bottom-2 h-0.5 rounded-full ${tone === 'pink' ? 'bg-brand-pink shadow-[0_0_12px_rgba(255,59,124,.8)]' : 'bg-brand-cyan shadow-[0_0_12px_rgba(0,215,215,.8)]'}`} />}</>}</NavLink>)}</div></nav>
}

export default function App() {
  const client = useQueryClient()
  const auth = useQuery({ queryKey: ['auth-status'], queryFn: api.authStatus, retry: false, staleTime: 60_000 })
  const [, setLastSync] = useState<string>()
  const [refreshing, setRefreshing] = useState(false)
  const refresh = async () => { setRefreshing(true); try { await Promise.all([client.fetchQuery({ queryKey: ['campuses'], queryFn: () => api.campuses(true) }), client.fetchQuery({ queryKey: ['projects'], queryFn: () => api.projects(true) })]); setLastSync(new Date().toISOString()) } finally { setRefreshing(false) } }
  const logout = () => { client.setQueryData(['auth-status'], { auth_required: true, authenticated: false, user: null }); void api.logout().finally(() => window.location.replace('/?logged_out=1')) }
  if (auth.isPending) return <main className="grid min-h-screen place-items-center bg-ink text-brand-cyan"><LoaderCircle size={30} className="animate-spin" /></main>
  const params = new URLSearchParams(window.location.search)
  const reason = params.get('reason') || (params.get('auth') === 'failed' ? 'failed' : undefined)
  if (auth.isError) return <LoginGate reason="failed" />
  if (auth.data?.auth_required && !auth.data.authenticated) return <LoginGate reason={reason} />
  return <Layout><Topbar onRefresh={refresh} refreshing={refreshing} user={auth.data?.user} onLogout={logout} /><Navigation /><Routes><Route path="/" element={<Navigate to="/discover" replace />} /><Route path="/discover" element={<Discover />} /><Route path="/matches" element={<Matches />} /><Route path="/explore" element={<Dashboard onSync={setLastSync} />} /><Route path="*" element={<Navigate to="/discover" replace />} /></Routes></Layout>
}
