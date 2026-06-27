'use client'
import { useState, useEffect } from 'react'
import api from '@/lib/api'

interface Division {
  id: string
  name: string
  slug?: string
  law_count: number
}

interface ParsedResult {
  title: string
  law_number?: string
  year?: number
  division_id: string
  division_name: string
  total_parts: number
  total_articles: number
  parsed_structure: any
  raw_text_preview?: string
}

export default function AdminUploadPage() {
  const [divisions, setDivisions] = useState<Division[]>([])
  const [selectedDivision, setSelectedDivision] = useState('')
  const [lawTitle, setLawTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ParsedResult | null>(null)
  const [error, setError] = useState('')
  const [step, setStep] = useState<'upload' | 'review' | 'done'>('upload')
  const [confirmLoading, setConfirmLoading] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')
  const [useAdvancedOcr, setUseAdvancedOcr] = useState(false)

  useEffect(() => {
    api.get('/divisions')
      .then(res => setDivisions(res.data))
      .catch(() => setError('فشل تحميل التصنيفات'))
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) setFile(e.target.files[0])
  }

  const handleUpload = async () => {
    if (!file || !selectedDivision) {
      setError('يرجى اختيار ملف PDF وتصنيف')
      return
    }
    setLoading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('division_id', selectedDivision)
      if (lawTitle) formData.append('law_title', lawTitle)
      formData.append('use_advanced_ocr', String(useAdvancedOcr))

      const res = await api.post('/admin/parse-ocr-pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 600000,
      })
      setResult(res.data.data)
      setStep('review')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'فشل معالجة الملف')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async () => {
    if (!result) return
    setConfirmLoading(true)
    setError('')
    try {
      const res = await api.post('/admin/confirm-parse', {
        title: result.title,
        division_id: result.division_id,
        division_name: result.division_name,
        parsed_structure: result.parsed_structure,
      })
      setSuccessMessage(res.data.message)
      setStep('done')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'فشل تأكيد الإدراج')
    } finally {
      setConfirmLoading(false)
    }
  }

  const handleReset = () => {
    setStep('upload')
    setResult(null)
    setFile(null)
    setLawTitle('')
    setSuccessMessage('')
    setError('')
  }

  const renderStructure = (structure: any, depth = 0) => {
    if (!structure) return null
    const parts = structure.parts || []
    return (
      <div className="space-y-2" style={{ marginRight: depth * 20 }}>
        {parts.map((part: any, pIdx: number) => (
          <div key={pIdx} className="border-r-4 border-blue-500 pr-3 py-2">
            <div className="font-bold text-blue-700">الباب {part.part_number}: {part.title}</div>
            {part.chapters && part.chapters.length > 0 && (
              <div className="mr-4 space-y-1 mt-1">
                {part.chapters.map((ch: any, cIdx: number) => (
                  <div key={cIdx} className="border-r-3 border-green-400 pr-3 py-1">
                    <div className="font-semibold text-green-700 text-sm">الفصل {ch.chapter_number}: {ch.title}</div>
                    <div className="mr-3 text-xs text-gray-600">
                      {ch.articles?.length || 0} مادة
                    </div>
                  </div>
                ))}
              </div>
            )}
            {(!part.chapters || part.chapters.length === 0) && (
              <div className="mr-4 text-xs text-gray-600">
                {part.articles?.length || 0} مادة
              </div>
            )}
          </div>
        ))}
      </div>
    )
  }

  if (step === 'done') {
    return (
      <main className="max-w-4xl mx-auto px-4 py-10">
        <div className="card text-center">
          <div className="text-5xl mb-4">✅</div>
          <h1 className="text-2xl font-bold text-green-700 mb-4">تم الإدراج بنجاح</h1>
          <p className="text-gray-700 mb-6">{successMessage}</p>
          <button onClick={handleReset} className="btn-primary">رفع قانون آخر</button>
        </div>
      </main>
    )
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold text-red-700 mb-8">رفع قانون جديد (PDF)</h1>

      {step === 'upload' && (
        <div className="card space-y-6">
          <div>
            <label className="block font-bold mb-2">التصنيف القانوني</label>
            <select
              value={selectedDivision}
              onChange={e => setSelectedDivision(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg"
            >
              <option value="">اختر التصنيف...</option>
              {divisions.map(d => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.law_count} قانون)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-bold mb-2">عنوان القانون (اختياري)</label>
            <input
              type="text"
              value={lawTitle}
              onChange={e => setLawTitle(e.target.value)}
              placeholder="سيتم استخراجه تلقائياً من الملف"
              className="w-full px-4 py-2 border rounded-lg"
            />
          </div>

          <div>
            <label className="block font-bold mb-2">ملف PDF</label>
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="w-full px-4 py-2 border rounded-lg"
            />
            <p className="text-sm text-gray-500 mt-1">يدعم الملفات النصية والممسوحة ضوئياً (مع OCR)</p>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="advancedOcr"
              checked={useAdvancedOcr}
              onChange={e => setUseAdvancedOcr(e.target.checked)}
            />
            <label htmlFor="advancedOcr">استخدام OCR متقدم (Google Vision) للملفات المصورة</label>
          </div>

          {error && <p className="text-red-600">{error}</p>}

          <button
            onClick={handleUpload}
            disabled={loading || !file || !selectedDivision}
            className="btn-primary !py-3 !px-8 disabled:opacity-50"
          >
            {loading ? 'جاري المعالجة...' : '🔍 معالجة واستخراج النصوص'}
          </button>
        </div>
      )}

      {step === 'review' && result && (
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-xl font-bold mb-4">مراجعة الهيكل المستخرج</h2>

            <div className="grid grid-cols-2 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
              <div>
                <span className="text-gray-600 text-sm">العنوان:</span>
                <span className="font-bold mr-2">{result.title}</span>
              </div>
              {result.law_number && (
                <div>
                  <span className="text-gray-600 text-sm">رقم القانون:</span>
                  <span className="font-bold mr-2">{result.law_number}</span>
                </div>
              )}
              {result.year && (
                <div>
                  <span className="text-gray-600 text-sm">السنة:</span>
                  <span className="font-bold mr-2">{result.year}</span>
                </div>
              )}
              <div>
                <span className="text-gray-600 text-sm">التصنيف:</span>
                <span className="font-bold mr-2">{result.division_name}</span>
              </div>
              <div>
                <span className="text-gray-600 text-sm">عدد الأبواب:</span>
                <span className="font-bold mr-2">{result.total_parts}</span>
              </div>
              <div>
                <span className="text-gray-600 text-sm">عدد المواد:</span>
                <span className="font-bold mr-2 text-blue-700">{result.total_articles}</span>
              </div>
            </div>

            <h3 className="font-bold mb-3">الهيكل الهرمي:</h3>
            {renderStructure(result.parsed_structure)}

            {result.raw_text_preview && (
              <details className="mt-6">
                <summary className="cursor-pointer text-blue-600 font-bold">معاينة النص الخام</summary>
                <pre className="mt-2 p-4 bg-gray-100 rounded-lg text-sm max-h-60 overflow-y-auto whitespace-pre-wrap" dir="rtl">
                  {result.raw_text_preview}
                </pre>
              </details>
            )}
          </div>

          {error && <p className="text-red-600">{error}</p>}

          <div className="flex gap-4">
            <button
              onClick={handleConfirm}
              disabled={confirmLoading}
              className="bg-green-600 text-white px-8 py-3 rounded-lg font-bold hover:bg-green-700 disabled:opacity-50"
            >
              {confirmLoading ? 'جاري الإدراج...' : '✅ تأكيد وإدراج في قاعدة البيانات'}
            </button>
            <button
              onClick={handleReset}
              disabled={confirmLoading}
              className="bg-gray-200 text-gray-700 px-6 py-3 rounded-lg font-bold hover:bg-gray-300"
            >
              إلغاء
            </button>
          </div>
        </div>
      )}
    </main>
  )
}
