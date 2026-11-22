import type { ReactNode } from 'react'

/**
 * The product is intentionally a focused one-page workspace for now.
 * Existing route components remain available for a future navigation layer.
 */
export function Layout({ children }: { children: ReactNode }) {
  return <main className="min-h-screen">{children}</main>
}
