import * as Dialog from '@radix-ui/react-dialog'
import { ArrowDownUp, Download, ExternalLink, Search, X } from 'lucide-react'
import { useState } from 'react'
import type { Paginated, Student, StudentStatus } from '../types/api'
import { Avatar } from './Avatar'
import { Badge, Button, Card, Skeleton } from './ui'

const labels: Record<StudentStatus, string> = {
  searching_group: 'Searching for group',
  registered_without_team: 'Registered · no team',
  not_registered: 'Not registered',
  uncertain: 'Uncertain',
  active_team: 'Active team',
  working_solo: 'Working on project',
  completed: 'Completed',
}

const tone = (status: StudentStatus) =>
  status === 'searching_group' || status === 'working_solo'
    ? 'green'
    : status === 'registered_without_team'
      ? 'blue'
      : status === 'uncertain'
        ? 'amber'
        : 'neutral'

type Props = {
  mode?: 'peer' | 'solo'
  data?: Paginated<Student>
  loading: boolean
  search: string
  setSearch: (value: string) => void
  status: string
  setStatus: (value: string) => void
  sort: string
  setSort: (value: 'login' | 'level' | '-level') => void
  exportUrl: (format: 'csv' | 'json') => string
}

export function StudentDirectory({
  mode = 'peer', data, loading, search, setSearch, status, setStatus, sort, setSort, exportUrl,
}: Props) {
  const [selected, setSelected] = useState<Student | null>(null)
  // "Uncertain" remains an evidence-safety classification when team data is
  // incomplete, but it is intentionally not a user-facing filter option.
  const statuses = (mode === 'solo'
    ? ['working_solo', 'completed']
    : ['searching_group', 'registered_without_team', 'not_registered', 'active_team', 'completed']) as StudentStatus[]

  return <Card className="overflow-hidden">
    <div className="flex flex-col gap-3 border-b border-line px-5 py-4 md:flex-row md:items-center md:justify-between">
      <div>
        <h2 className="m-0 text-sm font-semibold text-white">{mode === 'solo' ? 'Students working on this project' : 'Student directory'}</h2>
        <p className="m-0 mt-1 text-xs text-slate-500">{mode === 'solo' ? 'Active API registrations for this solo project' : 'Students who may need a team, with evidence-aware status'}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-3 text-slate-600" />
          <input aria-label="Search students" value={search} onChange={event => setSearch(event.target.value)} placeholder="Login or name" className="h-10 w-44 rounded-lg border border-line bg-ink pl-9 pr-3 text-xs outline-none focus:border-accent/50" />
        </div>
        <select aria-label="Student status" value={status} onChange={event => setStatus(event.target.value)} className="h-10 rounded-lg border border-line bg-ink px-3 text-xs">
          <option value="">All statuses</option>
          {statuses.map(value => <option key={value} value={value}>{labels[value]}</option>)}
        </select>
        <Button variant="outline" onClick={() => setSort(sort === 'login' ? '-level' : sort === '-level' ? 'level' : 'login')}>
          <ArrowDownUp size={14} />{sort === 'login' ? 'Login' : sort === '-level' ? 'Level ↓' : 'Level ↑'}
        </Button>
        <a href={exportUrl('csv')}><Button variant="outline"><Download size={14} />CSV</Button></a>
        <a href={exportUrl('json')}><Button variant="outline"><Download size={14} />JSON</Button></a>
      </div>
    </div>

    <div className="max-h-[38rem] overflow-auto" data-testid="student-scroll-area">
      <table className="w-full min-w-[820px] border-collapse text-left">
        <thead className="sticky top-0 z-10 bg-[#0c1218] shadow-[0_1px_0_rgba(39,52,69,.85)]">
          <tr className="text-[10px] uppercase tracking-wider text-slate-600">
            {['Student', 'Campus / promotion', 'Level', 'Project status', mode === 'solo' ? 'Work status' : 'Team status', 'Profile'].map(heading => <th key={heading} className="px-5 py-3 font-semibold">{heading}</th>)}
          </tr>
        </thead>
        <tbody>
          {loading
            ? Array.from({ length: 7 }, (_, index) => <tr key={index} className="border-b border-line"><td colSpan={6} className="px-5 py-4"><Skeleton className="h-10 w-full" /></td></tr>)
            : data?.items.map(student => <tr key={student.id} onClick={() => setSelected(student)} className="cursor-pointer border-b border-line/80 transition hover:bg-white/[.025]">
              <td className="px-5 py-3"><div className="flex items-center gap-3"><Avatar imageUrl={student.image_url} login={student.login} displayName={student.display_name} /><div><div className="text-sm font-semibold text-slate-100">{student.login}</div><div className="text-xs text-slate-500">{student.display_name}</div></div></div></td>
              <td className="px-5 py-3"><div className="text-xs text-slate-300">{student.campus}</div><div className="text-[11px] text-slate-600">{student.promotion}</div></td>
              <td className="px-5 py-3 text-sm font-medium text-slate-300">{student.level?.toFixed(2) ?? '—'}</td>
              <td className="px-5 py-3 text-xs text-slate-400">{student.project_status.replaceAll('_', ' ')}</td>
              <td className="px-5 py-3"><Badge tone={tone(student.team_status)}>{labels[student.team_status]}</Badge></td>
              <td className="px-5 py-3"><a aria-label={`Open ${student.login} profile`} href={student.profile_url} target="_blank" rel="noreferrer" onClick={event => event.stopPropagation()} className="text-slate-500 hover:text-accent"><ExternalLink size={16} /></a></td>
            </tr>)}
        </tbody>
      </table>
      {!loading && !data?.items.length && <div className="px-5 py-14 text-center"><div className="text-sm font-medium text-slate-300">{mode === 'solo' ? 'No active students found for this project' : 'No students match these filters'}</div><p className="text-xs text-slate-600">{mode === 'solo' ? 'Try another promotion or include completed records.' : 'Try another status or search term.'}</p></div>}
    </div>
    <div className="border-t border-line px-5 py-4 text-xs text-slate-500">{data?.total ?? 0} results · Scroll to browse</div>

    <Dialog.Root open={!!selected} onOpenChange={open => !open && setSelected(null)}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm" />
        <Dialog.Content className="fixed bottom-0 right-0 top-0 z-50 w-full max-w-md overflow-y-auto border-l border-line bg-[#0c1218] p-6 shadow-2xl">
          <Dialog.Close className="absolute right-5 top-5 rounded-lg p-2 text-slate-500 hover:bg-white/5"><X size={18} /></Dialog.Close>
          {selected && <>
            <div className="flex items-center gap-4 pt-8"><Avatar imageUrl={selected.image_url} login={selected.login} displayName={selected.display_name} /><div><Dialog.Title className="text-xl font-bold text-white">{selected.display_name}</Dialog.Title><Dialog.Description className="text-sm text-slate-500">@{selected.login}</Dialog.Description></div></div>
            <div className="mt-8 space-y-4">
              <div className="rounded-xl border border-line bg-white/[.02] p-4"><div className="text-[10px] uppercase tracking-wider text-slate-600">Classification</div><div className="mt-2"><Badge tone={tone(selected.team_status)}>{labels[selected.team_status]}</Badge></div><p className="mb-0 mt-3 text-xs leading-5 text-slate-400">{selected.classification_reason}</p></div>
              {([['Campus', selected.campus], ['Promotion', selected.promotion], ['Cursus level', selected.level?.toFixed(2) ?? 'Unavailable'], ['Project status', selected.project_status.replaceAll('_', ' ')] ] as const).map(([key, value]) => <div key={key} className="flex justify-between border-b border-line pb-3 text-sm"><span className="text-slate-500">{key}</span><span className="text-slate-200">{value}</span></div>)}
              <a href={selected.profile_url} target="_blank" rel="noreferrer"><Button className="mt-3 w-full">Open 42 profile<ExternalLink size={15} /></Button></a>
            </div>
          </>}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  </Card>
}
