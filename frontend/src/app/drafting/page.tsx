'use client'
import { useState } from 'react'
import Navbar from '@/components/Navbar'
import api from '@/lib/api'

export default function DraftingPage() {
  const [docType, setDocType] = useState('claim')
  const [context, setContext] = useState('')
  const [instructions, setInstructions] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)

  const docTypes = [
    { value: 'claim', label: '????? ????' },
    { value: 'defense', label: '????? ????' },
    { value: 'memo', label: '????? ???????' },
    { value: 'appeal', label: '??? / ???????' },
    { value: 'contract', label: '???' },
  ]

  const handleDraft = async () => {
    if (!context.trim()) return
    setLoading(true)
    setResult('')
    try {
      const res = await api.post('/analysis/draft', { doc_type: docType, context, instructions })
      setResult(res.data.document)
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
        <h1 className="text-3xl font-bold mb-8 text-center">??????? ????????? ??????</h1>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-6">
          {docTypes.map((dt) => (
            <button key={dt.value} onClick={() => setDocType(dt.value)} className={px-3 py-2 rounded-lg text-sm font-medium transition-colors }>{dt.label}</button>
          ))}
        </div>

        <textarea
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="???? ?????? ?????? / ??????..."
          className="w-full h-40 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 resize-none mb-4"
        />

        <textarea
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          placeholder="??????? ?????? (???????)..."
          className="w-full h-20 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 resize-none mb-4"
        />

        <button onClick={handleDraft} disabled={loading || !context.trim()} className="btn-primary w-full">
          {loading ? '???? ???????...' : '????? ???????'}
        </button>

        {result && (
          <div className="card mt-8">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-primary-700">??????? ????????</h3>
              <button onClick={() => navigator.clipboard.writeText(result)} className="text-sm text-primary-600 hover:underline">???</button>
            </div>
            <div className="whitespace-pre-wrap text-gray-700 leading-relaxed">{result}</div>
          </div>
        )}
      </main>
    </>
  )
}
