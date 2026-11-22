import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, Heart, Layers3, LoaderCircle, MousePointerClick, Sparkles, X } from 'lucide-react'
import { api, type StudentProfile } from '../services/api'
import { Avatar } from '../components/Avatar'

const field = 'h-12 w-full rounded-xl border border-line bg-[#0b121c] px-4 text-sm text-slate-200 outline-none transition focus:border-brand-cyan/60 focus:ring-4 focus:ring-brand-cyan/10'

function Empty({ title, detail }: { title: string; detail: string }) {
  return <div className="glass-panel brand-border mx-auto max-w-3xl rounded-3xl p-10 text-center sm:p-14"><div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-brand-cyan/10 text-brand-cyan"><Layers3 size={24} /></div><h2 className="mt-5 text-xl font-bold text-white">{title}</h2><p className="mx-auto max-w-lg text-sm leading-6 text-slate-400">{detail}</p></div>
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

export function Discover() {
  const queryClient = useQueryClient()
  const projects = useQuery({ queryKey: ['discover-projects'], queryFn: api.discoverProjects })
  const [project, setProject] = useState<number>()
  const [dismissed, setDismissed] = useState<number[]>([])
  const candidates = useQuery({ queryKey: ['candidates', project], queryFn: () => api.candidates(project!), enabled: !!project })
  useEffect(() => { if (!project && projects.data?.items[0]) setProject(projects.data.items[0].id) }, [projects.data, project])
  useEffect(() => setDismissed([]), [project])
  const swipe = useMutation({ mutationFn: ({ id, direction }: { id: number; direction: 'left' | 'right' }) => api.swipe(id, project!, direction), onSuccess: result => { queryClient.invalidateQueries({ queryKey: ['candidates', project] }); if (result.matched) queryClient.invalidateQueries({ queryKey: ['matches'] }) }, onError: (_error, variables) => setDismissed(current => current.filter(id => id !== variables.id)) })
  const person = candidates.data?.items.find(candidate => !dismissed.includes(candidate.user_id))
  const act = (direction: 'left' | 'right') => { if (!person) return; setDismissed(current => [...current, person.user_id]); swipe.mutate({ id: person.user_id, direction }) }
  return <section className="relative mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:py-12">
    <div className="brand-orb left-1/2 top-32 h-80 w-80 -translate-x-1/2 bg-brand-pink opacity-[.12]" />
    <div className="relative mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between"><div><p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[.2em] text-brand-cyan"><Sparkles size={14} />Verified project peers</p><h1 className="m-0 font-display text-4xl font-black tracking-[-.04em] text-white sm:text-5xl">Find your next <span className="text-brand-pink">teammate</span></h1><p className="mb-0 mt-3 text-sm text-slate-500">Interested or pass—mutual interest becomes a match.</p></div><label className="w-full lg:max-w-sm"><span className="mb-2 block text-xs font-semibold uppercase tracking-widest text-slate-500">Choose project</span><select aria-label="Project" className={field} value={project || ''} onChange={event => setProject(Number(event.target.value))}><option value="">Choose a project</option>{projects.data?.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label></div>
    {projects.isLoading || candidates.isLoading ? <div className="grid min-h-96 place-items-center text-brand-cyan"><LoaderCircle size={30} className="animate-spin" /></div> : projects.isError || candidates.isError ? <Empty title="No eligible project scan" detail={(projects.error || candidates.error)?.message || 'Try again after the next 42 data refresh.'} /> : !projects.data?.items.length ? <Empty title="No projects to match right now" detail="Only subscribed, unlocked group projects from verified 42 data appear here." /> : !person ? <Empty title="You’re all caught up" detail="There are no additional verified peers for this project." /> : <><CandidateCard key={person.user_id} person={person} onSwipe={act} /><div className="mx-auto mt-7 flex max-w-md items-center justify-center gap-7"><button aria-label="Pass" className="grid h-16 w-16 place-items-center rounded-full border border-slate-600 bg-[#111925] text-slate-300 shadow-xl transition hover:-translate-y-1 hover:border-slate-400 hover:text-white active:scale-95" onClick={() => act('left')}><X size={27} /></button><button aria-label="Interested" className="grid h-16 w-16 place-items-center rounded-full border border-pink-200/50 bg-brand-pink text-white shadow-[0_12px_40px_rgba(255,59,124,.38)] transition hover:-translate-y-1 hover:bg-[#ff578d] active:scale-95" onClick={() => act('right')}><Heart size={27} fill="currentColor" /></button></div><p className="mt-4 text-center text-xs text-slate-600">Pass <span className="mx-2 text-slate-700">·</span> Interested</p></>}
  </section>
}

export function Matches() {
  const matches = useQuery({ queryKey: ['matches'], queryFn: api.matches })
  return <section className="relative mx-auto max-w-6xl px-5 py-8 sm:px-8 lg:py-12"><div className="brand-orb -right-20 top-16 h-80 w-80 bg-brand-pink opacity-[.14]" /><div className="relative"><p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[.2em] text-brand-pink"><Heart size={14} fill="currentColor" />Mutual interest</p><h1 className="m-0 font-display text-4xl font-black tracking-[-.04em] text-white sm:text-5xl">Your <span className="text-brand-pink">matches</span></h1><p className="mt-3 text-slate-400">You both chose Interested for the same 42 project.</p><div className="mt-8 grid gap-4 md:grid-cols-2">{matches.data?.items.map(match => <article key={match.id} onClick={() => match.profile.profile_url && window.open(match.profile.profile_url, '_blank', 'noopener,noreferrer')} className="glass-panel brand-border group cursor-pointer rounded-3xl p-5 transition hover:-translate-y-1 hover:shadow-pink-glow"><div className="flex items-center gap-4"><div className="relative"><Avatar imageUrl={match.profile.image_url || undefined} login={match.profile.login} displayName={match.profile.display_name} className="h-16 w-16 rounded-2xl object-cover" /><span className="absolute -bottom-1 -right-1 grid h-6 w-6 place-items-center rounded-full border-2 border-[#0d1520] bg-brand-pink text-white"><Heart size={11} fill="currentColor" /></span></div><div className="min-w-0 flex-1"><h2 className="m-0 truncate text-lg font-bold text-white">{match.profile.display_name}</h2><p className="m-0 mt-1 truncate text-sm font-medium text-brand-cyan">{match.project_name}</p><p className="m-0 mt-1 text-xs text-slate-500">@{match.profile.login}</p></div><ExternalLink size={17} className="text-slate-600 transition group-hover:text-brand-pink" /></div><p className="mb-0 mt-5 border-t border-white/[.06] pt-4 text-xs text-slate-500">Verified through 42 Intra · tap to open profile</p></article>)}{!matches.data?.items.length && !matches.isLoading && <div className="md:col-span-2"><Empty title="No matches yet" detail="A match appears when you and another eligible student both choose Interested for the same project." /></div>}</div></div></section>
}
