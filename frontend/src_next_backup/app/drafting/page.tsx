'use client'
import { useState, useRef } from 'react'
import api from '@/lib/api'

export default function DraftingPage() {
  const [docType, setDocType] = useState('claim')
  const [context, setContext] = useState('')
  const [instructions, setInstructions] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [fileName, setFileName] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const docTypes = [
    { value: 'claim', label: 'صحيفة دعوى' },
    { value: 'defense', label: 'مذكرة دفاع' },
    { value: 'memo', label: 'مذكرة قانونية' },
    { value: 'appeal', label: 'استئناف / تمييز' },
    { value: 'contract', label: 'عقد' },
  ]

  const docTypeLabels: Record<string, string> = {
    claim: 'صحيفة دعوى', defense: 'مذكرة دفاع', memo: 'مذكرة قانونية', appeal: 'استئناف / تمييز', contract: 'عقد'
  }

  const handleDraft = async () => {
    if (!context.trim()) return
    setLoading(true)
    setResult('')
    try {
      const res = await api.post('/analysis/draft', { doc_type: docType, context, instructions })
      setResult(res.data.document)
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
      setContext(res.data.text)
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

  const downloadPdf = async () => {
    if (!result) return
    setPdfLoading(true)
    try {
      const res = await api.post('/analysis/draft-to-pdf', {
        text: result,
        title: `${
          {
            claim: 'صحيفة دعوى',
            defense: 'مذكرة دفاع',
            memo: 'مذكرة قانونية',
            appeal: 'استئناف',
            contract: 'عقد',
          }[docType] || 'مستند'
        } - قانوني`,
        doc_type: docType
      }, { responseType: 'blob' })
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `${docTypeLabels[docType] || 'مستند'} - ${new Date().toLocaleDateString('ar-YE')}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'فشل إنشاء PDF')
    } finally { setPdfLoading(false) }
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-8 text-center">صياغة المستندات القانونية</h1>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-6">
        {docTypes.map((dt) => (
          <button key={dt.value} onClick={() => setDocType(dt.value)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${docType === dt.value ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700'}`}>
            {dt.label}
          </button>
        ))}
      </div>

      <div className="flex gap-3 mb-4">
        <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" onChange={handleFileChange}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm cursor-pointer" />
        {extracting && <span className="text-sm text-gray-500 self-center">جاري استخراج النص...</span>}
        {fileName && !extracting && <span className="text-sm text-green-600 self-center">{fileName}</span>}
      </div>

      <textarea
        value={context}
        onChange={(e) => setContext(e.target.value)}
        placeholder="أدخل تفاصيل القضية / الموضوع..."
        className="w-full h-40 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 resize-none mb-4"
      />

      <textarea
        value={instructions}
        onChange={(e) => setInstructions(e.target.value)}
        placeholder="تعليمات إضافية (اختياري)..."
        className="w-full h-20 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 resize-none mb-4"
      />

      <button onClick={handleDraft} disabled={loading || !context.trim()} className="btn-primary w-full">
        {loading ? 'جاري الصياغة...' : 'صياغة المستند'}
      </button>

      {result && (
        <div className="card mt-8">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-bold text-primary-700">المستند المُصاغ</h3>
            <div className="flex gap-2">
              <button onClick={() => navigator.clipboard.writeText(result)} className="text-sm text-primary-600 hover:underline">نسخ</button>
              <button onClick={downloadPdf} disabled={pdfLoading} className="text-sm bg-primary-100 text-primary-700 px-3 py-1 rounded hover:bg-primary-200">
                {pdfLoading ? 'جاري...' : '📄 تحميل PDF'}
              </button>
            </div>
          </div>
          <div className="whitespace-pre-wrap text-gray-700 leading-relaxed">{result}</div>
        </div>
      )}
    </main>
  )
}
