'use client'
import { useState, useRef } from 'react'
import api from '@/lib/api'

export default function AnalysisPage() {
  const [text, setText] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<'analyze' | 'query'>('analyze')
  const [sources, setSources] = useState<any[]>([])
  const [extracting, setExtracting] = useState(false)
  const [fileName, setFileName] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

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
      setResult(err.response?.data?.detail || 'حدث خطأ')
    } finally {
      setLoading(false)
    }
  }

  const extractFileText = async (file: File) => {
    setExtracting(true)
    setFileName(file.name)
    const form = new FormData()
    form.append('file', file)
    try {
      const res = await api.post('/analysis/extract-text', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      setText(res.data.text)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'فشل استخراج النص')
    } finally {
      setExtracting(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) extractFileText(file)
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-8 text-center">التحليل القانوني الذكي</h1>

      <div className="flex gap-3 mb-6 justify-center">
        <button onClick={() => setMode('analyze')} className={`px-5 py-2 rounded-lg font-medium transition-colors ${mode === 'analyze' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700'}`}>تحليل نص</button>
        <button onClick={() => setMode('query')} className={`px-5 py-2 rounded-lg font-medium transition-colors ${mode === 'query' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700'}`}>استعلام قانوني</button>
      </div>

      <div className="flex gap-3 mb-3">
        <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" onChange={handleFileChange}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm cursor-pointer" />
        {extracting && <span className="text-sm text-gray-500 self-center">جاري استخراج النص...</span>}
        {fileName && !extracting && <span className="text-sm text-green-600 self-center">{fileName}</span>}
      </div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={mode === 'analyze' ? 'الصق النص القانوني المراد تحليله...' : 'اكتب سؤالك القانوني هنا...'}
        className="w-full h-48 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 resize-none"
      />

      <button onClick={handleAnalyze} disabled={loading || !text.trim()} className="btn-primary w-full mt-4">
        {loading ? 'جاري التحليل...' : mode === 'analyze' ? 'تحليل' : 'استعلام'}
      </button>

      {result && (
        <div className="card mt-8">
          <h3 className="text-lg font-bold mb-3 text-primary-700">{mode === 'analyze' ? 'نتيجة التحليل' : 'الإجابة'}</h3>
          <div className="whitespace-pre-wrap text-gray-700 leading-relaxed">{result}</div>
          {sources.length > 0 && (
            <div className="mt-4 pt-4 border-t">
              <h4 className="font-bold text-sm text-gray-600 mb-2">المصادر:</h4>
              {sources.map((s, i) => (
                <div key={i} className="text-sm text-gray-500">• {s.title} (دقة: {(s.score * 100).toFixed(0)}%)</div>
              ))}
            </div>
          )}
        </div>
      )}
    </main>
  )
}
