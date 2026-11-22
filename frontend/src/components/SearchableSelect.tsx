import { ChevronDown, Search } from 'lucide-react'
import { useEffect, useId, useMemo, useRef, useState } from 'react'

export interface SearchableOption {
  id: number
  label: string
  description?: string
}

const field = 'h-11 w-full rounded-lg border border-line bg-[#0b1016] px-3 pr-10 text-sm text-slate-200 outline-none transition focus:border-accent/60 focus:ring-2 focus:ring-accent/10'

export function SearchableSelect({
  label,
  value,
  options,
  placeholder,
  onInputChange,
  onSelect,
}: {
  label: string
  value: string
  options: SearchableOption[]
  placeholder: string
  onInputChange: (value: string) => void
  onSelect: (option: SearchableOption) => void
}) {
  const [query, setQuery] = useState(value)
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const listId = useId()

  useEffect(() => setQuery(value), [value])
  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    const candidates = !needle || query === value
      ? options
      : options.filter(option => `${option.label} ${option.description ?? ''}`.toLowerCase().includes(needle))
    return candidates.slice(0, 80)
  }, [options, query, value])

  return <div ref={root} className="relative">
    <div className="relative">
      <input
        ref={input}
        aria-label={label}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        className={field}
        value={query}
        placeholder={placeholder}
        autoComplete="off"
        onFocus={event => { setOpen(true); event.currentTarget.select() }}
        onChange={event => {
          setQuery(event.target.value)
          setOpen(true)
          onInputChange(event.target.value)
        }}
        onKeyDown={event => {
          if (event.key === 'Escape') setOpen(false)
          if (event.key === 'ArrowDown') setOpen(true)
        }}
      />
      <button
        type="button"
        aria-label={`Open ${label} options`}
        onClick={() => { setOpen(current => !current); input.current?.focus() }}
        className="absolute inset-y-0 right-0 grid w-10 place-items-center text-slate-600 hover:text-slate-300"
      >
        {query && query !== value ? <Search size={14}/> : <ChevronDown size={14}/>} 
      </button>
    </div>
    {open && <div id={listId} role="listbox" className="absolute z-30 mt-2 max-h-72 w-full overflow-y-auto rounded-xl border border-line bg-[#0c1218] p-1.5 shadow-2xl shadow-black/50">
      {filtered.map(option => <button
        type="button"
        role="option"
        aria-selected={option.label === value}
        key={option.id}
        onMouseDown={event => event.preventDefault()}
        onClick={() => {
          setQuery(option.label)
          setOpen(false)
          onSelect(option)
        }}
        className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-slate-300 hover:bg-white/[.06] hover:text-white aria-selected:bg-accent/[.08] aria-selected:text-accent"
      >
        <span className="truncate">{option.label}</span>
        {option.description && <span className="shrink-0 text-xs text-slate-600">{option.description}</span>}
      </button>)}
      {!filtered.length && <div className="px-3 py-6 text-center text-xs text-slate-600">No matching options</div>}
    </div>}
  </div>
}
