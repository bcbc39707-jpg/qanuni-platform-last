'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import api from '@/lib/api'
import { useAuth } from '@/lib/auth'

export default function RegisterPage() {
  const [form, setForm] = useState({ email: '', password: '', full_name: '', phone: '', role: 'client' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const { setAuth } = useAuth()

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await api.post('/auth/register', form)
      const { user, access_token, refresh_token } = res.data
      setAuth(user, access_token, refresh_token)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'فشل في إنشاء الحساب')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <main className="max-w-md mx-auto px-4 py-16">
        <div className="card">
          <h1 className="text-2xl font-bold mb-6 text-center">إنشاء حساب جديد</h1>
          {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">{error}</div>}
          <form onSubmit={handleRegister} className="space-y-4">
            <input type="text" value={form.full_name} onChange={(e) => setForm({...form, full_name: e.target.value})} placeholder="الاسم الكامل" className="w-full px-4 py-3 border border-gray-300 rounded-lg" required />
            <input type="email" value={form.email} onChange={(e) => setForm({...form, email: e.target.value})} placeholder="البريد الإلكتروني" className="w-full px-4 py-3 border border-gray-300 rounded-lg" required />
            <input type="tel" value={form.phone} onChange={(e) => setForm({...form, phone: e.target.value})} placeholder="رقم الهاتف" className="w-full px-4 py-3 border border-gray-300 rounded-lg" />
            <input type="password" value={form.password} onChange={(e) => setForm({...form, password: e.target.value})} placeholder="كلمة المرور" className="w-full px-4 py-3 border border-gray-300 rounded-lg" required />
            <select value={form.role} onChange={(e) => setForm({...form, role: e.target.value})} className="w-full px-4 py-3 border border-gray-300 rounded-lg">
              <option value="client">عميل / مواطن</option>
              <option value="lawyer">محامي</option>
            </select>
            <button type="submit" disabled={loading} className="btn-primary w-full">{loading ? 'جاري إنشاء الحساب...' : 'تسجيل'}</button>
          </form>
          <p className="text-center text-gray-600 mt-4 text-sm">لديك حساب؟ <Link href="/login" className="text-primary-600 hover:underline">تسجيل دخول</Link></p>
        </div>
      </main>
    </>
  )
}
