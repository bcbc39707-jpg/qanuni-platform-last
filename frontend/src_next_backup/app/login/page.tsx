'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import api from '@/lib/api'
import { useAuth } from '@/lib/auth'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const { setAuth } = useAuth()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await api.post('/auth/login', { email, password })
      const { user, access_token, refresh_token } = res.data
      setAuth(user, access_token, refresh_token)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'فشل في عملية تسجيل الدخول')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <main className="max-w-md mx-auto px-4 py-16">
        <div className="card">
          <h1 className="text-2xl font-bold mb-6 text-center">تسجيل الدخول</h1>
          {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">{error}</div>}
          <form onSubmit={handleLogin} className="space-y-4">
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="البريد الإلكتروني" className="w-full px-4 py-3 border border-gray-300 rounded-lg" required />
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="كلمة المرور" className="w-full px-4 py-3 border border-gray-300 rounded-lg" required />
            <button type="submit" disabled={loading} className="btn-primary w-full">{loading ? 'جاري تسجيل الدخول...' : 'دخول'}</button>
          </form>
          <p className="text-center text-gray-600 mt-4 text-sm">ليس لديك حساب؟ <Link href="/register" className="text-primary-600 hover:underline">إنشاء حساب</Link></p>
        </div>
      </main>
    </>
  )
}
