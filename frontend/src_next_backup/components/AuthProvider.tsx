'use client'
import { useEffect } from 'react'
import { useAuth } from '@/lib/auth'

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const hydrate = useAuth((s) => s.hydrate)
  useEffect(() => { hydrate() }, [hydrate])
  return <>{children}</>
}
