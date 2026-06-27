'use client'
import { useState, useEffect } from 'react'
import api from '@/lib/api'

export default function AdminCasesPage() {
  const [cases, setCases] = useState<any[]>([])
  const [caseType, setCaseType] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)

  const fetchCases = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (caseType) params.case_type = caseType
      if (status) params.status = status
      const res = await api.get('/admin/cases', { params })
      setCases(res.data)
    } catch { } finally { setLoading(false) }
  }

  useEffect(() => { fetchCases() }, [caseType, status])

  const deleteCase = async (id: string) => {
    if (!confirm('حذف القضية؟')) return
    try { await api.delete(`/admin/cases/${id}`); fetchCases() } catch { }
  }

  const typeLabels: Record<string, string> = { civil: 'مدني', criminal: 'جنائي', commercial: 'تجاري', family: 'أحوال شخصية', labor: 'عمالي', administrative: 'إداري' }
  const statusColors: Record<string, string> = { open: 'bg-green-100 text-green-700', in_progress: 'bg-amber-100 text-amber-700', closed: 'bg-gray-100 text-gray-700' }

  if (loading) return <main className="max-w-6xl mx-auto px-4 py-10"><p>جاري التحميل...</p></main>

  return (
    <main className="max-w-6xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-8 text-red-700">إدارة القضايا</h1>

      <div className="flex gap-3 mb-6">
        <select value={caseType} onChange={(e) => setCaseType(e.target.value)} className="px-3 py-2 border rounded-lg">
          <option value="">كل الأنواع</option>
          {Object.entries(typeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="px-3 py-2 border rounded-lg">
          <option value="">كل الحالات</option>
          <option value="open">مفتوحة</option>
          <option value="in_progress">قيد المعالجة</option>
          <option value="closed">مغلقة</option>
        </select>
      </div>

      <div className="space-y-3">
        {cases.map((c) => (
          <div key={c.id} className="card flex justify-between items-center">
            <div>
              <div className="font-bold">{c.title}</div>
              <div className="text-sm text-gray-500 mt-1">
                {typeLabels[c.case_type] || c.case_type} | {c.owner_name || c.owner_email}
                {c.lawyer_name && <span> | محامٍ: {c.lawyer_name}</span>}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-xs px-2 py-1 rounded ${statusColors[c.status] || 'bg-gray-100'}`}>{c.status}</span>
              <button onClick={() => deleteCase(c.id)} className="text-red-500 hover:text-red-700 text-sm">حذف</button>
            </div>
          </div>
        ))}
        {cases.length === 0 && <p className="text-gray-500 text-center">لا توجد قضايا</p>}
      </div>
    </main>
  )
}
