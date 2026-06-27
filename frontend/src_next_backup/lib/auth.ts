import { create } from 'zustand'

export interface User {
  id: string
  email: string
  full_name: string
  role: string
}

interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  setAuth: (user: User, accessToken: string, refreshToken?: string) => void
  logout: () => void
  isLoggedIn: () => boolean
  hydrate: () => void
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  refreshToken: null,
  setAuth: (user, accessToken, refreshToken) => {
    localStorage.setItem('token', accessToken)
    localStorage.setItem('user', JSON.stringify(user))
    if (refreshToken) localStorage.setItem('refresh_token', refreshToken)
    document.cookie = `token=${encodeURIComponent(accessToken)}; path=/; SameSite=Lax; max-age=${7 * 86400}`
    set({ user, token: accessToken, refreshToken })
  },
  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    document.cookie = 'token=; path=/; SameSite=Lax; max-age=0'
    set({ user: null, token: null, refreshToken: null })
  },
  isLoggedIn: () => {
    const token = get().token || (typeof window !== 'undefined' ? localStorage.getItem('token') : null)
    return !!token
  },
  hydrate: () => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token')
      const refreshToken = localStorage.getItem('refresh_token')
      const userStr = localStorage.getItem('user')
      if (token && userStr) {
        try {
          const user = JSON.parse(userStr) as User
          document.cookie = `token=${encodeURIComponent(token)}; path=/; SameSite=Lax; max-age=${7 * 86400}`
          set({ user, token, refreshToken })
        } catch {
          localStorage.removeItem('token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user')
          document.cookie = 'token=; path=/; SameSite=Lax; max-age=0'
        }
      }
    }
  },
}))
