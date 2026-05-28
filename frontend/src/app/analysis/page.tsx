'use client'
import { useState } from 'react'
import Navbar from '@/components/Navbar'
import api from '@/lib/api'

export default function AnalysisPage() {
  const [text, setText] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<'analyze' | 'query'>('analyze')
  const [sources, setSources] = useState<any[]>([])

  const handleAnalyze = async () => {
    if (!text.trim()) return
    setLoading(true)
    setResult('')
    setSources([])
    try {
      if (mode === 'analyze') {
        const res = await api.post('/analysis/analyze', { text, analysis_type: 'general' })
        setResult(res.data.analysis)
      } else {
        const res = await api.post('/analysis/query', { question: text, top_k: 5 })
        setResult(res.data.answer)
        setSources(res.data.sources || [])
      }
    } catch (err: any) {
      setResult(err.response?.data?.detail || '??? ???')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Navbar />
      <main className="max-w-4xl mx-auto px-4 py-10">
        <h1 className="text-3xl font-bold mb-8 text-center">??????? ???????? ?????</h1>

        <div className="flex gap-3 mb-6 justify-center">
          <button onClick={() => setMode('analyze')} className={px-5 py-2 rounded-lg font-medium transition-colors }>????? ????</button>
          <button onClick={() => setMode('query')} className={px-5 py-2 rounded-lg font-medium transition-colors }>???? ??????</button>
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={mode === 'analyze' ? '???? ?? ?????? ?? ??????? ???????...' : '???? ????? ????????...'}
          className="w-full h-48 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 resize-none"
        />

        <button onClick={handleAnalyze} disabled={loading || !text.trim()} className="btn-primary w-full mt-4">
          {loading ? '???? ???????...' : mode === 'analyze' ? '?????' : '????? ??????'}
        </button>

        {result && (
          <div className="card mt-8">
            <h3 className="text-lg font-bold mb-3 text-primary-700">{mode === 'analyze' ? '????? ???????' : '???????'}</h3>
            <div className="whitespace-pre-wrap text-gray-700 leading-relaxed">{result}</div>
            {sources.length > 0 && (
              <div className="mt-4 pt-4 border-t">
                <h4 className="font-bold text-sm text-gray-600 mb-2">???????:</h4>
                {sources.map((s, i) => (
                  <div key={i} className="text-sm text-gray-500">• {s.title} (???: {(s.score * 100).toFixed(0)}%)</div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </>
  )
}
