import * as Select from '@radix-ui/react-select'
import { Check, ChevronDown } from 'lucide-react'

export interface DropdownOption {
  value: string
  label: string
}

export function DropdownSelect({
  label,
  value,
  options,
  placeholder,
  disabled,
  onChange,
}: {
  label: string
  value: string
  options: DropdownOption[]
  placeholder?: string
  disabled?: boolean
  onChange: (value: string) => void
}) {
  return <Select.Root value={value} onValueChange={onChange} disabled={disabled}>
    <Select.Trigger
      aria-label={label}
      className="flex h-11 w-full items-center justify-between gap-3 rounded-xl border border-line bg-[#0a111b] px-3 text-sm text-slate-200 outline-none transition hover:border-slate-600 focus:border-brand-cyan/60 focus:ring-4 focus:ring-brand-cyan/10 data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50"
    >
      <span className="min-w-0 flex-1 truncate text-left"><Select.Value placeholder={placeholder} /></span>
      <Select.Icon className="shrink-0 text-slate-600 transition-colors"><ChevronDown aria-hidden size={14} /></Select.Icon>
    </Select.Trigger>
    <Select.Portal>
      <Select.Content
        position="popper"
        sideOffset={8}
        collisionPadding={12}
        className="glass-panel z-50 max-h-72 w-[var(--radix-select-trigger-width)] overflow-hidden rounded-xl border border-line shadow-2xl shadow-black/50"
      >
        <Select.Viewport className="p-1.5">
          {options.map(option => <Select.Item
            key={option.value}
            value={option.value}
            className="relative flex cursor-pointer select-none items-center rounded-lg py-2.5 pl-3 pr-9 text-sm text-slate-300 outline-none transition data-[highlighted]:bg-white/[.06] data-[highlighted]:text-white data-[state=checked]:bg-brand-cyan/[.08] data-[state=checked]:text-brand-cyan"
          >
            <Select.ItemText>{option.label}</Select.ItemText>
            <Select.ItemIndicator className="absolute right-3 inline-flex text-brand-cyan"><Check aria-hidden size={14} /></Select.ItemIndicator>
          </Select.Item>)}
        </Select.Viewport>
      </Select.Content>
    </Select.Portal>
  </Select.Root>
}
