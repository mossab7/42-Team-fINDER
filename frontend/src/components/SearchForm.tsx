import { CalendarDays, ChevronDown, SlidersHorizontal, Star } from 'lucide-react'
import type { FormEvent, SelectHTMLAttributes } from 'react'
import type { Campus, Project, ProjectConfiguration, PromotionType, ScanConfig } from '../types/api'
import { Button, Card, Skeleton } from './ui'
import { SearchableSelect } from './SearchableSelect'

const field = 'h-11 w-full rounded-xl border border-line bg-[#0a111b] px-3 text-sm text-slate-200 outline-none transition focus:border-brand-cyan/60 focus:ring-4 focus:ring-brand-cyan/10'

function NativeSelect({ children, className = '', ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <div className="relative">
    <select {...props} className={`${field} appearance-none pr-10 ${className}`}>{children}</select>
    <ChevronDown aria-hidden size={16} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-500" />
  </div>
}

export function SearchForm({
  config, setConfig, campuses, projects, years, projectConfiguration,
  projectConfigurationLoading, onMaxSizeChange, loading, onSubmit, onSave, scanning, saved,
}: {
  config: ScanConfig
  setConfig: (value: ScanConfig) => void
  campuses?: Campus[]
  projects?: Project[]
  years?: number[]
  projectConfiguration?: ProjectConfiguration
  projectConfigurationLoading?: boolean
  onMaxSizeChange?: (value: number) => void
  loading: boolean
  onSubmit: () => void
  onSave?: () => void
  scanning: boolean
  saved?: boolean
}) {
  const change = <K extends keyof ScanConfig>(key: K, value: ScanConfig[K]) => setConfig({ ...config, [key]: value })
  const promotion = (key: string, value: string | number) => change('promotion', { ...config.promotion, [key]: value })
  const submit = (event: FormEvent) => { event.preventDefault(); onSubmit() }
  const minTeamSize = projectConfiguration?.min_team_size ?? 1
  const maxTeamSize = projectConfiguration?.max_team_size ?? 20
  const teamSizes = Array.from({ length: maxTeamSize - minTeamSize + 1 }, (_, index) => minTeamSize + index)
  const sizeNote = projectConfigurationLoading
    ? 'Checking the 42 project session…'
    : projectConfiguration?.solo
      ? 'Solo project · team matching is disabled'
      : projectConfiguration?.maximum_source === 'fallback'
        ? '42 did not expose a team maximum · using fallback 5'
        : projectConfiguration
          ? `42 team range: ${projectConfiguration.min_team_size}–${projectConfiguration.max_team_size} · default ${projectConfiguration.max_team_size}`
          : ''

  if (loading) return <Card className="p-5"><div className="grid gap-4 md:grid-cols-4">{[1, 2, 3, 4].map(item => <Skeleton key={item} className="h-16" />)}</div></Card>

  return <Card className="brand-border overflow-visible">
    <div className="flex items-center justify-between border-b border-line px-5 py-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-white"><SlidersHorizontal size={16} className="text-brand-pink" />Search criteria</div>
      <div className="text-xs text-slate-500">Selections are remembered on this device</div>
    </div>
    <form onSubmit={submit} className="p-5">
      <div className="grid gap-4 xl:grid-cols-12">
        <label className="xl:col-span-3">
          <span className="mb-2 block text-sm font-medium text-slate-400">Campus</span>
          <SearchableSelect label="Campus" value={config.campus_name} placeholder="Search campus…" options={(campuses ?? []).map(campus => ({ id: campus.id, label: campus.name, description: campus.city }))} onInputChange={() => setConfig({ ...config, campus_id: 0, project_solo: false })} onSelect={option => setConfig({ ...config, campus_name: option.label, campus_id: option.id, project_solo: false })} />
        </label>
        <label className="xl:col-span-2">
          <span className="mb-2 block text-sm font-medium text-slate-400">Promotion definition</span>
          <NativeSelect aria-label="Promotion definition" value={config.promotion.type} onChange={event => promotion('type', event.target.value as PromotionType)}>
            <option value="cursus_year">Cursus enrollment year</option><option value="piscine">Piscine year / month</option><option value="date_range">Enrollment date range</option>
          </NativeSelect>
        </label>
        {config.promotion.type === 'date_range' ? <div className="grid grid-cols-2 gap-2 xl:col-span-3">
          <label><span className="mb-2 block text-xs font-medium text-slate-400">From</span><input aria-label="Enrollment start" type="date" className={field} value={config.promotion.start_date ?? ''} onChange={event => promotion('start_date', event.target.value)} /></label>
          <label><span className="mb-2 block text-xs font-medium text-slate-400">To</span><input aria-label="Enrollment end" type="date" className={field} value={config.promotion.end_date ?? ''} onChange={event => promotion('end_date', event.target.value)} /></label>
        </div> : <>
          <label className="xl:col-span-2">
            <span className="mb-2 block text-xs font-medium text-slate-400">{config.promotion.type === 'piscine' ? 'Piscine year' : 'Promotion'}</span>
            <NativeSelect aria-label="Promotion year" value={config.promotion.year ?? ''} onChange={event => promotion('year', Number(event.target.value))}>
              <option value="">Select year</option>{years?.map(year => <option key={year}>{year}</option>)}
            </NativeSelect>
          </label>
          {config.promotion.type === 'piscine' && <label className="xl:col-span-1">
            <span className="mb-2 block text-xs font-medium text-slate-400">Month</span>
            <NativeSelect aria-label="Piscine month" value={config.promotion.month ?? 9} onChange={event => promotion('month', Number(event.target.value))}>
              {Array.from({ length: 12 }, (_, index) => <option key={index} value={index + 1}>{new Date(2000, index, 1).toLocaleString('en', { month: 'short' })}</option>)}
            </NativeSelect>
          </label>}
        </>}
        <label className="xl:col-span-3">
          <span className="mb-2 block text-sm font-medium text-slate-400">Project</span>
          <SearchableSelect label="Project" value={config.project_name} placeholder="Search project…" options={(projects ?? []).map(project => ({ id: project.id, label: project.name, description: project.slug }))} onInputChange={() => setConfig({ ...config, project_id: 0, project_solo: false })} onSelect={option => setConfig({ ...config, project_name: option.label, project_id: option.id, project_solo: false })} />
        </label>
        <label className="xl:col-span-2">
          <span className="mb-2 block text-sm font-medium text-slate-400">Team size limit</span>
          <NativeSelect aria-label="Maximum team size" disabled={projectConfiguration?.solo} value={config.max_team_size} onChange={event => onMaxSizeChange ? onMaxSizeChange(Number(event.target.value)) : change('max_team_size', Number(event.target.value))}>
            {teamSizes.map(size => <option key={size}>{size}</option>)}
          </NativeSelect>
          <span className="mt-2 block text-xs leading-4 text-slate-500">{sizeNote}</span>
        </label>
        <div className="flex items-end xl:col-span-2"><Button className="h-11 w-full" type="submit" disabled={scanning || projectConfigurationLoading || !config.campus_id || !config.project_id || (!config.promotion.year && config.promotion.type !== 'date_range')}><CalendarDays size={16} />{scanning ? 'Scanning…' : projectConfiguration?.solo ? 'Find active students' : 'Find teammates'}</Button></div>
      </div>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-500"><input type="checkbox" checked={config.include_unavailable} onChange={event => change('include_unavailable', event.target.checked)} className="accent-brand-pink" />Show completed and unavailable records in results</label>
        {onSave && <Button type="button" variant="ghost" onClick={onSave} disabled={!config.campus_id || !config.project_id}><Star size={14} />{saved ? 'Saved' : 'Save search'}</Button>}
      </div>
    </form>
  </Card>
}
