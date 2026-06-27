'use client'
import { useState } from 'react'
import api from '@/lib/api'

export default function AdminRagPage() {
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [reindexLoading, setReindexLoading] = useState(false)
  const [msg, setMsg] = useState('')

  const checkStatus = async () => {
    setLoading(true)
    try {
      const res = await api.get('/admin/rag/status')
      setStatus(res.data)
    } catch { setStatus({ status: 'error' }) } finally { setLoading(false) }
  }

  const reindex = async () => {
    setReindexLoading(true)
    setMsg('')
    try {
      const res = await api.post('/admin/rag/reindex')
      setMsg(`تمت الفهرسة: ${res.data.chunks_indexed} مقطع`)
      checkStatus()
    } catch (err: any) {
      setMsg(err.response?.data?.detail || 'خطأ')
    } finally { setReindexLoading(false) }
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-8 text-red-700">إدارة RAG</h1>

      <div className="card mb-6">
        <h3 className="font-bold text-lg mb-2">حالة قاعدة المعرفة</h3>
        {!status ? (
          <button onClick={checkStatus} disabled={loading} className="btn-primary !py-2">
            {loading ? 'جاري...' : 'فحص الحالة'}
          </button>
        ) : (
          <div className="text-sm">
            <p>الحالة: {status.status === 'connected' ? '🟢 متصل' : '🔴 غير متصل'}</p>
            {status.collection && (
              <p>عدد المتجهات: {status.collection.vectors_count}</p>
            )}
            {status.error && <p className="text-red-500">{status.error}</p>}
          </div>
        )}
      </div>

      <div className="card">
        <h3 className="font-bold text-lg mb-2">إعادة فهرسة RAG</h3>
        <p className="text-gray-600 mb-4">مسح وإعادة فهرسة جميع القوانين والأحكام في Qdrant.</p>
        <button onClick={reindex} disabled={reindexLoading} className="btn-primary">
          {reindexLoading ? 'جاري الفهرسة...' : 'إعادة فهرسة RAG'}
        </button>
        {msg && <p className="mt-4 text-sm text-green-600">{msg}</p>}
      </div>
    </main>
  )
}
