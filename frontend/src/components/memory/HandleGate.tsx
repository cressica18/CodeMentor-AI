import { FormEvent, useState } from 'react'
import { Search } from 'lucide-react'

interface Props {
  initial: string
  onSubmit: (handle: string) => void
  placeholder?: string
}

/**
 * Small reusable "which CF handle's memory am I viewing" input, shown at
 * the top of every Phase 3 memory page so each page works standalone
 * even before a shared handle has been set elsewhere in the app.
 */
export default function HandleGate({ initial, onSubmit, placeholder }: Props) {
  const [value, setValue] = useState(initial)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (value.trim()) onSubmit(value.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-3 mb-6">
      <div className="relative flex-1 max-w-sm">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder ?? 'Enter Codeforces handle, e.g. tourist'}
          className="input w-full pl-9 pr-4 py-2"
        />
      </div>
      <button type="submit" className="btn-primary">
        Load
      </button>
    </form>
  )
}
