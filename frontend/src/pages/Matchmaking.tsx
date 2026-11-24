import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BadgeCheck, ChevronDown, ExternalLink, FolderKanban, Heart, Layers3, LoaderCircle, MousePointerClick, Sparkles, Unlock, X } from 'lucide-react'
import { api, type MatchProject, type StudentProfile } from '../services/api'
import { Avatar } from '../components/Avatar'

function Empty({ title, detail }: { title: string; detail: string }) {
  return <div className="glass-panel brand-border mx-auto max-w-3xl rounded-3xl p-10 text-center sm:p-14"><div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-brand-cyan/10 text-brand-cyan"><Layers3 size={24} /></div><h2 className="mt-5 text-xl font-bold text-white">{title}</h2><p className="mx-auto max-w-lg text-sm leading-6 text-slate-400">{detail}</p></div>
}

function ProjectPicker({ items, value, onChange }: { items: MatchProject[]; value?: number; onChange: (projectId: number) => void }) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const selected = items.find(item => item.id === value)
  const groups = [
    { state: 'subscribed' as const, title: 'Subscribed projects', icon: BadgeCheck },
    { state: 'eligible' as const, title: 'Eligible on Intra', icon: Unlock },
  ]

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  return <div ref={root} className="relative z-30 w-full lg:max-w-sm">
    <span className="mb-2 block text-xs font-semibold uppercase tracking-widest text-slate-500">Choose project</span>
    <button type="button" aria-label="Project" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(current => !current)} className="brand-border glass-panel group relative flex min-h-16 w-full items-center gap-3 overflow-hidden rounded-2xl px-4 text-left outline-none transition hover:-translate-y-0.5 hover:shadow-[0_14px_40px_rgba(0,215,215,.12)] focus:ring-4 focus:ring-brand-cyan/10">
      <span className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-brand-cyan to-brand-pink" />
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-brand-cyan/20 bg-brand-cyan/10 text-brand-cyan"><FolderKanban size={19} /></span>
      <span className="min-w-0 flex-1"><span className="block truncate text-sm font-bold text-white">{selected?.name || 'Select a team project'}</span><span className={`mt-1 block text-[11px] font-semibold uppercase tracking-[.12em] ${selected?.subscription_status === 'eligible' ? 'text-brand-pink' : 'text-brand-cyan'}`}>{selected?.subscription_status === 'eligible' ? 'Eligible · subscribe on Intra' : selected ? 'Subscribed · ready to match' : 'Your 42 project path'}</span></span>
      <ChevronDown size={16} className={`shrink-0 text-slate-500 transition ${open ? 'rotate-180 text-brand-cyan' : ''}`} />
    </button>
    {open && <div role="listbox" aria-label="Team projects" className="glass-panel brand-border absolute right-0 z-50 mt-2 max-h-[26rem] w-full overflow-y-auto rounded-2xl p-2 shadow-2xl shadow-black/60">
      {groups.map(group => {
        const options = items.filter(item => item.subscription_status === group.state)
        if (!options.length) return null
        const Icon = group.icon
        return <div key={group.state} className="py-1"><div className={`flex items-center gap-2 px-3 py-2 text-[10px] font-bold uppercase tracking-[.16em] ${group.state === 'eligible' ? 'text-brand-pink' : 'text-brand-cyan'}`}><Icon size={12} />{group.title}</div>{options.map(item => <button key={item.id} type="button" role="option" aria-selected={item.id === value} onClick={() => { onChange(item.id); setOpen(false) }} className="group/option flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left transition hover:bg-white/[.06] aria-selected:bg-brand-cyan/[.08]">
          <span className={`h-2 w-2 shrink-0 rounded-full ${group.state === 'eligible' ? 'bg-brand-pink shadow-[0_0_10px_rgba(255,59,124,.8)]' : 'bg-brand-cyan shadow-[0_0_10px_rgba(0,215,215,.8)]'}`} />
          <span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold text-slate-200 group-hover/option:text-white">{item.name}</span><span className="mt-0.5 block text-[11px] text-slate-500">{group.state === 'eligible' ? 'Available to subscribe' : 'Matching enabled'}</span></span>
          {item.id === value && <BadgeCheck size={16} className="shrink-0 text-brand-cyan" />}
        </button>)}</div>
      })}
    </div>}
  </div>
}

function CandidateCard({ person, onSwipe }: { person: StudentProfile; onSwipe: (direction: 'left' | 'right') => void }) {
  const start = useRef<number>()
  const ignoreClick = useRef(false)
  const [dx, setDx] = useState(0)
  const [drag, setDrag] = useState(false)
  const move = (event: React.PointerEvent) => { if (start.current !== undefined) setDx(event.clientX - start.current) }
  const end = () => {
    if (start.current === undefined) return
    const x = dx
    start.current = undefined
    setDrag(false)
    setDx(0)
    if (Math.abs(x) > 90) { ignoreClick.current = true; onSwipe(x > 0 ? 'right' : 'left') }
  }
  const openProfile = () => {
    if (ignoreClick.current) { ignoreClick.current = false; return }
    if (person.profile_url) window.open(person.profile_url, '_blank', 'noopener,noreferrer')
  }
  const tilt = Math.max(-7, Math.min(7, dx / 24))
  return <article title="Open 42 profile" role="link" tabIndex={0} onKeyDown={event => { if (event.key === 'Enter') openProfile() }} onClick={openProfile} onPointerDown={event => { start.current = event.clientX; setDrag(true); event.currentTarget.setPointerCapture(event.pointerId) }} onPointerMove={move} onPointerUp={end} onPointerCancel={end} className="brand-border glass-panel relative mx-auto w-full max-w-md cursor-grab select-none overflow-hidden rounded-[2rem] shadow-card active:cursor-grabbing" style={{ transform: `translateX(${dx}px) rotate(${tilt}deg)`, transition: drag ? 'none' : 'transform .18s ease-out', touchAction: 'pan-y' }}>
    <div className="relative h-32 overflow-hidden bg-gradient-to-br from-brand-cyan/25 via-[#131c2b] to-brand-pink/25"><div className="absolute -left-16 -top-20 h-44 w-44 rounded-full bg-brand-cyan/25 blur-3xl" /><div className="absolute -right-14 -top-16 h-44 w-44 rounded-full bg-brand-pink/25 blur-3xl" /><div className="absolute right-5 top-5 inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-black/25 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[.14em] text-slate-200 backdrop-blur"><Sparkles size={12} className="text-brand-pink" />Verified peer</div></div>
    {dx > 35 && <div className="pointer-events-none absolute left-6 top-20 z-20 -rotate-12 rounded-xl border-2 border-brand-pink px-3 py-1 text-lg font-black uppercase tracking-widest text-brand-pink">Interested</div>}
    {dx < -35 && <div className="pointer-events-none absolute right-6 top-20 z-20 rotate-12 rounded-xl border-2 border-slate-400 px-3 py-1 text-lg font-black uppercase tracking-widest text-slate-300">Pass</div>}
    <div className="-mt-14 px-6 pb-6">
      <Avatar imageUrl={person.image_url || undefined} login={person.login} displayName={person.display_name} className="relative h-28 w-28 rounded-3xl border-4 border-[#0b121c] object-cover shadow-xl" />
      <div className="mt-4 flex items-start justify-between gap-3"><div className="min-w-0"><h2 className="m-0 truncate text-2xl font-extrabold tracking-tight text-white">{person.display_name}</h2><p className="mt-1 text-sm font-medium text-brand-cyan">@{person.login}{person.level != null && ` · level ${person.level.toFixed(1)}`}</p></div><span className="shrink-0 rounded-full border border-white/10 bg-white/[.04] px-3 py-1.5 text-xs text-slate-300">{person.campus_name || '42 student'}</span></div>
      <div className="mt-6 flex items-center justify-between border-t border-white/[.06] pt-4 text-xs text-slate-500"><span className="inline-flex items-center gap-1.5"><MousePointerClick size={13} />Tap for Intra profile</span><span>Swipe to choose</span></div>
    </div>
  </article>
}

const celebrationParticles = Array.from({ length: 30 }, (_, index) => {
  const angle = (index / 30) * Math.PI * 2
  const distance = 120 + (index % 5) * 34
  return {
    x: Math.cos(angle) * distance,
    y: Math.sin(angle) * distance,
    delay: (index % 6) * 0.045,
    symbol: index % 4 === 0 ? '♥' : '✦',
    size: 12 + (index % 4) * 5,
  }
})

function MatchCelebration({ person, onClose }: { person: StudentProfile; onClose: () => void }) {
  return <div role="dialog" aria-modal="true" aria-labelledby="match-title" className="fixed inset-0 z-50 grid place-items-center overflow-hidden bg-[#03060b]/80 p-5 backdrop-blur-lg" onClick={onClose}>
    <div aria-hidden className="pointer-events-none absolute inset-0">
      {celebrationParticles.map((particle, index) => <span key={index} className={`match-sparkle absolute left-1/2 top-1/2 ${particle.symbol === '♥' ? 'text-brand-pink' : 'text-brand-cyan'}`} style={{ '--spark-x': `${particle.x}px`, '--spark-y': `${particle.y}px`, animationDelay: `${particle.delay}s`, fontSize: particle.size } as CSSProperties}>{particle.symbol}</span>)}
    </div>
    <section className="match-pop glass-panel brand-border relative w-full max-w-md overflow-hidden rounded-[2rem] p-7 text-center shadow-[0_30px_100px_rgba(255,59,124,.3)] sm:p-9" onClick={event => event.stopPropagation()}>
      <div className="absolute -left-20 -top-24 h-56 w-56 rounded-full bg-brand-cyan/20 blur-3xl" /><div className="absolute -right-20 -top-20 h-56 w-56 rounded-full bg-brand-pink/25 blur-3xl" />
      <div className="relative mx-auto w-fit"><Avatar imageUrl={person.image_url || undefined} login={person.login} displayName={person.display_name} className="h-28 w-28 rounded-[1.75rem] border-4 border-brand-pink/70 object-cover shadow-[0_0_40px_rgba(255,59,124,.3)]" fallbackClassName="grid h-28 w-28 place-items-center rounded-[1.75rem] border-4 border-brand-pink/70 bg-gradient-to-br from-brand-cyan/20 to-brand-pink/20 text-2xl font-black text-white" /><span className="absolute -bottom-3 -right-3 grid h-11 w-11 place-items-center rounded-full border-4 border-[#0d1520] bg-brand-pink text-white shadow-pink-glow"><Heart size={19} fill="currentColor" /></span></div>
      <p className="relative mb-2 mt-7 text-xs font-bold uppercase tracking-[.24em] text-brand-cyan">Mutual interest</p>
      <h2 id="match-title" className="relative m-0 font-display text-4xl font-black tracking-[-.04em] text-white">It’s a <span className="text-brand-pink">match!</span></h2>
      <p className="relative mx-auto mt-4 max-w-sm text-sm leading-6 text-slate-300"><strong className="text-white">{person.display_name}</strong> already swiped right on you too. You both want to team up.</p>
      <div className="relative mt-7 grid gap-3 sm:grid-cols-2"><button type="button" onClick={onClose} className="h-12 rounded-xl border border-line bg-white/[.035] px-4 text-sm font-semibold text-slate-200 transition hover:border-brand-cyan/40 hover:bg-brand-cyan/[.07]">Keep swiping</button><Link to="/matches" className="inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-brand-pink px-4 text-sm font-bold text-white shadow-pink-glow transition hover:-translate-y-0.5 hover:bg-[#ff578d]"><Heart size={16} fill="currentColor" />View matches</Link></div>
    </section>
  </div>
}

export function Discover() {
  const queryClient = useQueryClient()
  const projects = useQuery({
    queryKey: ['discover-projects'],
    queryFn: api.discoverProjects,
    refetchInterval: query => query.state.data?.catalog_ready === false ? 1500 : false,
  })
  const [project, setProject] = useState<number>()
  const [dismissed, setDismissed] = useState<number[]>([])
  const [matchedPerson, setMatchedPerson] = useState<StudentProfile>()
  const selectedProject = projects.data?.items.find(item => item.id === project)
  const canMatch = selectedProject?.subscription_status === 'subscribed'
  const candidates = useQuery({ queryKey: ['candidates', project], queryFn: () => api.candidates(project!), enabled: !!project && canMatch })
  useEffect(() => {
    if (!project) {
      const subscribed = projects.data?.items.find(item => item.subscription_status === 'subscribed')
      if (subscribed) setProject(subscribed.id)
    }
  }, [projects.data, project])
  useEffect(() => { setDismissed([]); setMatchedPerson(undefined) }, [project])
  const swipe = useMutation({ mutationFn: ({ id, direction }: { id: number; direction: 'left' | 'right' }) => api.swipe(id, project!, direction) })
  const person = candidates.data?.items.find(candidate => !dismissed.includes(candidate.user_id))
  const act = async (direction: 'left' | 'right') => {
    if (!person) return
    const swipedPerson = person
    setDismissed(current => [...current, swipedPerson.user_id])
    try {
      const result = await swipe.mutateAsync({ id: swipedPerson.user_id, direction })
      if (result.matched && direction === 'right') setMatchedPerson(swipedPerson)
      void queryClient.invalidateQueries({ queryKey: ['candidates', project] })
      if (result.matched) void queryClient.invalidateQueries({ queryKey: ['matches'] })
    } catch {
      setDismissed(current => current.filter(id => id !== swipedPerson.user_id))
    }
  }
  return <section className="relative mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:py-12">
    {matchedPerson && <MatchCelebration person={matchedPerson} onClose={() => setMatchedPerson(undefined)} />}
    <div className="brand-orb left-1/2 top-32 h-80 w-80 -translate-x-1/2 bg-brand-pink opacity-[.12]" />
    <div className="relative z-20 mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between"><div><p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[.2em] text-brand-cyan"><Sparkles size={14} />Verified project peers</p><h1 className="m-0 font-display text-4xl font-black tracking-[-.04em] text-white sm:text-5xl">Find your next <span className="text-brand-pink">teammate</span></h1><p className="mb-0 mt-3 text-sm text-slate-500">Interested or pass—mutual interest becomes a match.</p></div><ProjectPicker items={projects.data?.items ?? []} value={project} onChange={setProject} /></div>
    {projects.isLoading || (canMatch && candidates.isLoading) ? <div className="grid min-h-96 place-items-center text-brand-cyan"><LoaderCircle size={30} className="animate-spin" /></div> : projects.isError || (canMatch && candidates.isError) ? <Empty title="No eligible project scan" detail={(projects.error || candidates.error)?.message || 'Try again after the next 42 data refresh.'} /> : !projects.data?.items.length ? <Empty title="No team projects available right now" detail="Unlocked team projects will appear here when 42 marks you as subscribed or eligible to subscribe." /> : !selectedProject ? <Empty title="Choose a project" detail="Select a subscribed project to discover peers, or an eligible project to open its enrollment page on 42 Intra." /> : !canMatch ? <div className="brand-border glass-panel mx-auto max-w-2xl overflow-hidden rounded-3xl p-8 text-center sm:p-11"><div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl border border-brand-pink/20 bg-brand-pink/10 text-brand-pink shadow-pink-glow"><Unlock size={27} /></div><p className="mb-2 mt-6 text-xs font-bold uppercase tracking-[.2em] text-brand-pink">Eligible · not subscribed</p><h2 className="m-0 text-2xl font-black text-white">Subscribe to {selectedProject.name} first</h2><p className="mx-auto mt-4 max-w-lg text-sm leading-6 text-slate-400">42 Intra shows that you are eligible for this team project, but matching is available only after you subscribe. Enroll on your school Intra, then return and refresh the page.</p><a href={selectedProject.slug ? `https://projects.intra.42.fr/projects/${encodeURIComponent(selectedProject.slug)}` : 'https://projects.intra.42.fr/'} target="_blank" rel="noreferrer" className="mt-6 inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-brand-cyan px-5 text-sm font-bold text-[#041316] shadow-[0_0_30px_rgba(0,215,215,.22)] transition hover:-translate-y-0.5 hover:bg-[#35ebeb]">Subscribe on 42 Intra<ExternalLink size={16} /></a></div> : !person ? <Empty title="You’re all caught up" detail="There are no additional verified peers for this project." /> : <><CandidateCard key={person.user_id} person={person} onSwipe={act} /><div className="mx-auto mt-7 flex max-w-md items-center justify-center gap-7"><button aria-label="Pass" className="grid h-16 w-16 place-items-center rounded-full border border-slate-600 bg-[#111925] text-slate-300 shadow-xl transition hover:-translate-y-1 hover:border-slate-400 hover:text-white active:scale-95" onClick={() => act('left')}><X size={27} /></button><button aria-label="Interested" className="grid h-16 w-16 place-items-center rounded-full border border-pink-200/50 bg-brand-pink text-white shadow-[0_12px_40px_rgba(255,59,124,.38)] transition hover:-translate-y-1 hover:bg-[#ff578d] active:scale-95" onClick={() => act('right')}><Heart size={27} fill="currentColor" /></button></div><p className="mt-4 text-center text-xs text-slate-600">Pass <span className="mx-2 text-slate-700">·</span> Interested</p></>}
  </section>
}

export function Matches() {
  const matches = useQuery({ queryKey: ['matches'], queryFn: api.matches })
  return <section className="relative mx-auto max-w-6xl px-5 py-8 sm:px-8 lg:py-12"><div className="brand-orb -right-20 top-16 h-80 w-80 bg-brand-pink opacity-[.14]" /><div className="relative"><p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[.2em] text-brand-pink"><Heart size={14} fill="currentColor" />Mutual interest</p><h1 className="m-0 font-display text-4xl font-black tracking-[-.04em] text-white sm:text-5xl">Your <span className="text-brand-pink">matches</span></h1><p className="mt-3 text-slate-400">You both chose Interested for the same 42 project.</p><div className="mt-8 grid gap-4 md:grid-cols-2">{matches.data?.items.map(match => <article key={match.id} onClick={() => match.profile.profile_url && window.open(match.profile.profile_url, '_blank', 'noopener,noreferrer')} className="glass-panel brand-border group cursor-pointer rounded-3xl p-5 transition hover:-translate-y-1 hover:shadow-pink-glow"><div className="flex items-center gap-4"><div className="relative"><Avatar imageUrl={match.profile.image_url || undefined} login={match.profile.login} displayName={match.profile.display_name} className="h-16 w-16 rounded-2xl object-cover" /><span className="absolute -bottom-1 -right-1 grid h-6 w-6 place-items-center rounded-full border-2 border-[#0d1520] bg-brand-pink text-white"><Heart size={11} fill="currentColor" /></span></div><div className="min-w-0 flex-1"><h2 className="m-0 truncate text-lg font-bold text-white">{match.profile.display_name}</h2><p className="m-0 mt-1 truncate text-sm font-medium text-brand-cyan">{match.project_name}</p><p className="m-0 mt-1 text-xs text-slate-500">@{match.profile.login}</p></div><ExternalLink size={17} className="text-slate-600 transition group-hover:text-brand-pink" /></div><p className="mb-0 mt-5 border-t border-white/[.06] pt-4 text-xs text-slate-500">Verified through 42 Intra · tap to open profile</p></article>)}{!matches.data?.items.length && !matches.isLoading && <div className="md:col-span-2"><Empty title="No matches yet" detail="A match appears when you and another eligible student both choose Interested for the same project." /></div>}</div></div></section>
}
