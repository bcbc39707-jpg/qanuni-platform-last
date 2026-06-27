'use client'
import { useState, useEffect } from 'react'
import api from '@/lib/api'

export default function AdminSubscriptionsPage() {
  const [subs, setSubs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const fetchSubs = async () => {
    setLoading(true)
    try {
      const res = await api.get('/admin/subscriptions')
      setSubs(res.data)
    } catch { } finally { setLoading(false) }
  }

  useEffect(() => { fetchSubs() }, [])

  const updatePlan = async (id: string, plan: string) => {
    try { await api.put(`/admin/subscriptions/${id}`, { plan }); fetchSubs() } catch { }
  }

  const planColors: Record<string, string> = { free: 'bg-gray-100 text-gray-600', professional: 'bg-blue-100 text-blue-700', enterprise: 'bg-purple-100 text-purple-700' }
  const planLabels: Record<string, string> = { free: 'مجاني', professional: 'احترافي', enterprise: 'مؤسسي' }

  if (loading) return <main className="max-w-6xl mx-auto px-4 py-10"><p>جاري التحميل...</p></main>

  return (
    <main className="max-w-6xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-8 text-red-700">إدارة الاشتراكات</h1>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-100 text-right">
              <th className="p-3">المستخدم</th><th className="p-3">الخطة</th><th className="p-3">البحث</th><th className="p-3">التحليل</th><th className="p-3">الصياغة</th><th className="p-3">الحالة</th>
            </tr>
          </thead>
          <tbody>
            {subs.map((s) => (
              <tr key={s.id} className="border-b hover:bg-gray-50">
                <td className="p-3">{s.user_name || s.user_email}</td>
                <td className="p-3">
                  <select value={s.plan} onChange={(e) => updatePlan(s.id, e.target.value)} className="text-sm border rounded px-2 py-1">
                    {Object.entries(planLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </td>
                <td className="p-3 text-sm">{s.searches_used}/{s.search_quota}</td>
                <td className="p-3 text-sm">{s.analyses_used}/{s.analysis_quota}</td>
                <td className="p-3 text-sm">{s.drafts_used}/{s.drafting_quota}</td>
                <td className="p-3"><span className={`text-xs px-2 py-1 rounded ${s.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{s.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  )
}
