'use client'
import { useState } from 'react'
import api from '@/lib/api'

interface SearchResult {
  id: string
  title: string
  snippet: string
  doc_type: string
  score: number
}

const PAGE_SIZE = 10

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [docType, setDocType] = useState('')
  const [page, setPage] = useState(1)

  const handleSearch = async (e: React.FormEvent, pageNum = 1) => {
    e?.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setPage(pageNum)
    try {
      const res = await api.get('/search', { params: { q: query, doc_type: docType || undefined, page: pageNum, size: PAGE_SIZE } })
      setResults(res.data.results)
      setTotal(res.data.total)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)
  const docTypeLabels: Record<string, string> = { law: 'قانون', ruling: 'حكم', document: 'مستند' }

  return (
    <>
      <main className="max-w-5xl mx-auto px-4 py-10">
        <h1 className="text-3xl font-bold mb-8 text-center">البحث القانوني</h1>
        <form onSubmit={(e) => handleSearch(e, 1)} className="mb-8">
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="ابحث في القوانين والأحكام والمستندات..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <select value={docType} onChange={(e) => setDocType(e.target.value)} className="px-4 py-3 border border-gray-300 rounded-lg">
              <option value="">الكل</option>
              <option value="law">التشريعات</option>
              <option value="ruling">الأحكام</option>
              <option value="document">المستندات</option>
            </select>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? 'جاري البحث...' : 'بحث'}
            </button>
          </div>
        </form>

        {total > 0 && <p className="text-gray-600 mb-4">تم العثور على {total} نتيجة</p>}

        <div className="space-y-4">
          {results.map((r) => (
            <div key={r.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-lg font-bold text-primary-700">{r.title}</h3>
                <span className="text-xs bg-primary-100 text-primary-700 px-2 py-1 rounded">{docTypeLabels[r.doc_type] || r.doc_type}</span>
              </div>
              <p className="text-gray-600" dangerouslySetInnerHTML={{ __html: r.snippet }} />
            </div>
          ))}
        </div>

        {totalPages > 1 && (
          <div className="flex justify-center gap-2 mt-8" dir="ltr">
            <button onClick={() => handleSearch(undefined as any, page - 1)} disabled={page <= 1} className="px-3 py-1.5 border rounded-lg disabled:opacity-30 hover:bg-gray-50">السابق</button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button key={p} onClick={() => handleSearch(undefined as any, p)} className={`px-3 py-1.5 border rounded-lg ${p === page ? 'bg-primary-600 text-white' : 'hover:bg-gray-50'}`}>{p}</button>
            ))}
            <button onClick={() => handleSearch(undefined as any, page + 1)} disabled={page >= totalPages} className="px-3 py-1.5 border rounded-lg disabled:opacity-30 hover:bg-gray-50">التالي</button>
          </div>
        )}

        {results.length === 0 && query && !loading && (
          <p className="text-center text-gray-500 mt-10">لا توجد نتائج. حاول تغيير كلمات البحث.</p>
        )}
      </main>
    </>
  )
}
