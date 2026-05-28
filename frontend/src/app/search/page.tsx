'use client'
import { useState } from 'react'
import Navbar from '@/components/Navbar'
import api from '@/lib/api'

interface SearchResult {
  id: string
  title: string
  snippet: string
  doc_type: string
  score: number
}

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [docType, setDocType] = useState('')

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    try {
      const res = await api.get('/search', { params: { q: query, doc_type: docType || undefined } })
      setResults(res.data.results)
      setTotal(res.data.total)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const docTypeLabels: Record<string, string> = { law: '?????', ruling: '???', document: '?????' }

  return (
    <>
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 py-10">
        <h1 className="text-3xl font-bold mb-8 text-center">????? ????????</h1>
        <form onSubmit={handleSearch} className="mb-8">
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="???? ?? ???????? ???????? ???????..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <select value={docType} onChange={(e) => setDocType(e.target.value)} className="px-4 py-3 border border-gray-300 rounded-lg">
              <option value="">????</option>
              <option value="law">????????</option>
              <option value="ruling">???????</option>
              <option value="document">???????</option>
            </select>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? '???? ?????...' : '???'}
            </button>
          </div>
        </form>

        {total > 0 && <p className="text-gray-600 mb-4">?? ?????? ??? {total} ?????</p>}

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

        {results.length === 0 && query && !loading && (
          <p className="text-center text-gray-500 mt-10">?? ???? ?????. ??? ????? ??? ??????.</p>
        )}
      </main>
    </>
  )
}
