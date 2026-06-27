'use client'
import { useState, useEffect } from 'react'
import api from '@/lib/api'

export default function AdminContentPage() {
  const [items, setItems] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [type, setType] = useState('')
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)

  const fetchContent = async () => {
    setLoading(true)
    try {
      const res = await api.get('/admin/content', { params: { type: type || undefined, q: q || undefined } })
      setItems(res.data.items)
      setTotal(res.data.total)
    } catch { } finally { setLoading(false) }
  }

  useEffect(() => { fetchContent() }, [type])

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); fetchContent() }

  const deleteItem = async (id: string, t: string) => {
    if (!confirm('هل أنت متأكد من الحذف؟')) return
    try { await api.delete(`/admin/content/${id}`, { params: { type: t } }); fetchContent() } catch { }
  }

  const typeLabels: Record<string, string> = { law: 'قانون', ruling: 'حكم' }
  const typeColors: Record<string, string> = { law: 'bg-blue-100 text-blue-700', ruling: 'bg-amber-100 text-amber-700' }

  if (loading) return <main className="max-w-6xl mx-auto px-4 py-10"><p>جاري التحميل...</p></main>

  return (
    <main className="max-w-6xl mx-auto px-4 py-10">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-red-700">إدارة المحتوى</h1>
        <div className="flex gap-2">
          <button onClick={() => setType('')} className={`px-3 py-1.5 rounded text-sm ${!type ? 'bg-primary-600 text-white' : 'bg-gray-100'}`}>الكل</button>
          <button onClick={() => setType('law')} className={`px-3 py-1.5 rounded text-sm ${type === 'law' ? 'bg-primary-600 text-white' : 'bg-gray-100'}`}>قوانين</button>
          <button onClick={() => setType('ruling')} className={`px-3 py-1.5 rounded text-sm ${type === 'ruling' ? 'bg-primary-600 text-white' : 'bg-gray-100'}`}>أحكام</button>
        </div>
      </div>

      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-3">
          <input type="text" value={q} onChange={(e) => setQ(e.target.value)} placeholder="بحث في المحتوى..." className="flex-1 px-4 py-2 border rounded-lg" />
          <button type="submit" className="btn-primary !py-2">بحث</button>
        </div>
      </form>

      <p className="text-gray-600 mb-4">إجمالي: {total}</p>

      <div className="space-y-3">
        {items.map((item: any) => (
          <div key={item.id} className="card flex justify-between items-center">
            <div>
              <div className="font-bold">{item.title}</div>
              <div className="text-sm text-gray-500 mt-1">
                <span className={`text-xs px-2 py-0.5 rounded ${typeColors[item.type] || 'bg-gray-100'}`}>{typeLabels[item.type] || item.type}</span>
                {item.year && <span className="mr-2">{item.year}</span>}
                {item.category && <span className="mr-2">{item.category}</span>}
              </div>
            </div>
            <button onClick={() => deleteItem(item.id, item.type)} className="text-red-500 hover:text-red-700 text-sm">حذف</button>
          </div>
        ))}
        {items.length === 0 && <p className="text-gray-500 text-center">لا يوجد محتوى</p>}
      </div>
    </main>
  )
}
