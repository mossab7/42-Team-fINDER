import { useEffect, useState } from 'react'

function avatarSource(imageUrl?: string) {
  if (!imageUrl) return undefined
  try {
    const parsed = new URL(imageUrl)
    if (parsed.protocol === 'https:' && parsed.hostname === 'cdn.intra.42.fr') {
      return `/api/avatars?url=${encodeURIComponent(imageUrl)}`
    }
  } catch {
    return undefined
  }
  return imageUrl
}

export function Avatar({
  imageUrl,
  login,
  displayName,
  className = 'h-9 w-9 rounded-full border border-line object-cover',
  fallbackClassName = 'grid h-9 w-9 place-items-center rounded-full border border-brand-cyan/20 bg-gradient-to-br from-brand-cyan/15 to-brand-pink/15 text-xs font-bold text-brand-cyan',
}: {
  imageUrl?: string
  login: string
  displayName: string
  className?: string
  fallbackClassName?: string
}) {
  const source = avatarSource(imageUrl)
  const [failed, setFailed] = useState(false)

  useEffect(() => setFailed(false), [source])

  if (!source || failed) {
    return <div data-testid={`avatar-fallback-${login}`} aria-label={`${displayName} initials`} className={fallbackClassName}>{login.slice(0, 2).toUpperCase()}</div>
  }
  return <img alt={`${displayName} avatar`} src={source} onError={() => setFailed(true)} className={className}/>
}
