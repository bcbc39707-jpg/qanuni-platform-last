'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import api from '@/lib/api'

const typeLabels: Record<string, string> = { civil: 'مدني', criminal: 'جنائي', commercial: 'تجاري', family: 'أحوال شخصية', labor: 'عمالي', administrative: 'إداري' }
const statusColors: Record<string, string> = { open: 'bg-green-100 text-green-700', in_progress: 'bg-amber-100 text-amber-700', closed: 'bg-gray-100 text-gray-700', archived: 'bg-red-100 text-red-700' }

export default function CasesPage() {
  const [cases, setCases] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ title: '', case_type: 'civil', description: '', court_name: '' })

  useEffect(() => { api.get('/cases').then(r => setCases(r.data)).catch(() => {}) }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const res = await api.post('/cases', form)
      setCases([{...res.data, created_at: null}, ...cases])
      setShowForm(false)
      setForm({ title: '', case_type: 'civil', description: '', court_name: '' })
    } catch {}
  }

  return (
    <>
      <main className="max-w-5xl mx-auto px-4 py-10">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">القضايا</h1>
          <button onClick={() => setShowForm(!showForm)} className="btn-primary">+ قضية جديدة</button>
        </div>

        {showForm && (
          <form onSubmit={handleCreate} className="card mb-6 space-y-3">
            <input type="text" value={form.title} onChange={(e) => setForm({...form, title: e.target.value})} placeholder="عنوان القضية" className="w-full px-4 py-2 border rounded-lg" required />
            <select value={form.case_type} onChange={(e) => setForm({...form, case_type: e.target.value})} className="w-full px-4 py-2 border rounded-lg">
              <option value="civil">مدني</option><option value="criminal">جنائي</option><option value="commercial">تجاري</option><option value="family">أحوال شخصية</option><option value="labor">عمالي</option><option value="administrative">إداري</option>
            </select>
            <textarea value={form.description} onChange={(e) => setForm({...form, description: e.target.value})} placeholder="وصف القضية" className="w-full px-4 py-2 border rounded-lg h-24 resize-none" />
            <button type="submit" className="btn-primary">إنشاء</button>
          </form>
        )}

        <div className="space-y-3">
          {cases.map((c) => (
            <Link href={`/cases/${c.id}`} key={c.id} className="card flex justify-between items-center hover:shadow-md transition-shadow">
              <div>
                <div className="font-bold">{c.title}</div>
                <div className="text-sm text-gray-500">{typeLabels[c.case_type] || c.case_type}</div>
              </div>
              <span className={`text-xs px-2 py-1 rounded ${statusColors[c.status] || 'bg-gray-100'}`}>{c.status}</span>
            </Link>
          ))}
          {cases.length === 0 && <p className="text-gray-500 text-center">لا توجد قضايا. أضف قضيتك الأولى!</p>}
        </div>
      </main>
    </>
  )
}
