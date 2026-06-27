'use client'
import { useState } from 'react'
import api from '@/lib/api'

export default function AdminIndexPage() {
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const rebuildIndex = async () => {
    setLoading(true)
    setMessage('')
    try {
      const res = await api.post('/admin/reindex-search')
      setMessage(res.data.detail || 'تم إعادة بناء الفهارس')
    } catch (err: any) {
      setMessage(err.response?.data?.detail || 'حدث خطأ')
    } finally { setLoading(false) }
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-8 text-red-700">إدارة فهارس البحث</h1>
      <div className="card">
        <h3 className="font-bold text-lg mb-2">فهارس البحث النصي</h3>
        <p className="text-gray-600 mb-4">إعادة بناء فهارس البحث النصي في قاعدة البيانات. قد تستغرق العملية بضع ثوانٍ.</p>
        <button onClick={rebuildIndex} disabled={loading} className="btn-primary">
          {loading ? 'جاري إعادة البناء...' : 'إعادة بناء الفهارس'}
        </button>
        {message && <p className="mt-4 text-sm text-green-600">{message}</p>}
      </div>
    </main>
  )
}
