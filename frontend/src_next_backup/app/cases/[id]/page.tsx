'use client'
import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import api from '@/lib/api'

interface Document {
  id: string
  title: string
  doc_type: string
  file_size: number | null
  ocr_confidence: number | null
  ocr_method: string | null
  created_at: string | null
}

interface CaseDetail {
  id: string
  title: string
  description: string | null
  case_number: string | null
  case_type: string
  status: string
  court_name: string | null
  documents: Document[]
}

interface Usage {
  advanced_ocr_left: number
  advanced_ocr_quota: number
}

export default function CaseDetailPage() {
  const { id } = useParams()
  const router = useRouter()
  const [caseData, setCaseData] = useState<CaseDetail | null>(null)
  const [usage, setUsage] = useState<Usage | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [reprocessing, setReprocessing] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ title: '', description: '', status: '' })
  const [error, setError] = useState('')

  useEffect(() => {
    api.get(`/cases/${id}`).then((res) => {
      setCaseData(res.data)
      setForm({ title: res.data.title, description: res.data.description || '', status: res.data.status })
    }).catch(() => router.push('/cases')).finally(() => setLoading(false))
    api.get('/subscriptions/usage').then((res) => setUsage(res.data)).catch(() => {})
  }, [id, router])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    fd.append('title', file.name)
    fd.append('case_id', id as string)
    try {
      await api.post('/documents/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      const res = await api.get(`/cases/${id}`)
      setCaseData(res.data)
      api.get('/subscriptions/usage').then((r) => setUsage(r.data)).catch(() => {})
    } catch { setError('فشل رفع الملف') }
    finally { setUploading(false) }
  }

  const handleAdvancedScan = async (docId: string) => {
    setReprocessing(docId)
    try {
      await api.post(`/documents/${docId}/reprocess-advanced`)
      const res = await api.get(`/cases/${id}`)
      setCaseData(res.data)
      api.get('/subscriptions/usage').then((r) => setUsage(r.data)).catch(() => {})
    } catch (err: any) {
      setError(err.response?.data?.detail || 'فشل المسح المتقدم')
    }
    finally { setReprocessing(null) }
  }

  const handleDelete = async () => {
    if (!confirm('هل أنت متأكد من حذف هذه القضية؟')) return
    try {
      await api.delete(`/cases/${id}`)
      router.push('/cases')
    } catch { setError('فشل حذف القضية') }
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const res = await api.put(`/cases/${id}`, form)
      setCaseData(res.data)
      setEditing(false)
    } catch { setError('فشل تحديث القضية') }
  }

  const handleDeleteDoc = async (docId: string) => {
    if (!confirm('هل أنت متأكد من حذف هذا المستند؟')) return
    try {
      await api.delete(`/documents/${docId}`)
      const res = await api.get(`/cases/${id}`)
      setCaseData(res.data)
    } catch { setError('فشل حذف المستند') }
  }

  const statusColors: Record<string, string> = { open: 'bg-green-100 text-green-700', in_progress: 'bg-amber-100 text-amber-700', closed: 'bg-gray-100 text-gray-700', archived: 'bg-red-100 text-red-700' }
  const typeLabels: Record<string, string> = { civil: 'مدني', criminal: 'جنائي', commercial: 'تجاري', family: 'أحوال شخصية', labor: 'عمالي', administrative: 'إداري' }

  if (loading) return <main className="max-w-4xl mx-auto px-4 py-10"><p className="text-center">جاري التحميل...</p></main>
  if (!caseData) return <main className="max-w-4xl mx-auto px-4 py-10"><p className="text-center">القضية غير موجودة</p></main>

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">{error}</div>}

      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-3xl font-bold">{caseData.title}</h1>
          <div className="flex gap-3 mt-2 text-sm text-gray-600">
            <span className={`px-2 py-0.5 rounded ${statusColors[caseData.status] || 'bg-gray-100'}`}>{caseData.status}</span>
            <span>{typeLabels[caseData.case_type] || caseData.case_type}</span>
            {caseData.court_name && <span>{caseData.court_name}</span>}
            {caseData.case_number && <span>رقم: {caseData.case_number}</span>}
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setEditing(!editing)} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">تعديل</button>
          <button onClick={handleDelete} className="px-4 py-2 text-sm border border-red-300 text-red-600 rounded-lg hover:bg-red-50">حذف</button>
        </div>
      </div>

      {editing && (
        <form onSubmit={handleUpdate} className="card mb-6 space-y-3">
          <input type="text" value={form.title} onChange={(e) => setForm({...form, title: e.target.value})} className="w-full px-4 py-2 border rounded-lg" required />
          <textarea value={form.description} onChange={(e) => setForm({...form, description: e.target.value})} className="w-full px-4 py-2 border rounded-lg h-24 resize-none" />
          <select value={form.status} onChange={(e) => setForm({...form, status: e.target.value})} className="w-full px-4 py-2 border rounded-lg">
            <option value="open">مفتوحة</option><option value="in_progress">قيد الإجراء</option><option value="closed">مغلقة</option><option value="archived">مؤرشفة</option>
          </select>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary">حفظ</button>
            <button type="button" onClick={() => setEditing(false)} className="px-4 py-2 border rounded-lg">إلغاء</button>
          </div>
        </form>
      )}

      {caseData.description && <p className="text-gray-700 mb-6">{caseData.description}</p>}

      <div className="card mb-6">
        <h2 className="font-bold text-lg mb-3">المستندات</h2>
        <label className="flex items-center justify-center border-2 border-dashed border-gray-300 rounded-lg p-6 cursor-pointer hover:border-primary-400 mb-4">
          <span className="text-gray-500">{uploading ? 'جاري الرفع...' : '+ إضافة مستند'}</span>
          <input type="file" onChange={handleUpload} className="hidden" disabled={uploading} />
        </label>
        {caseData.documents.length === 0 ? (
          <p className="text-gray-500 text-sm">لا توجد مستندات مرفوعة</p>
        ) : (
          <div className="space-y-2">
            {caseData.documents.map((doc) => (
              <div key={doc.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{doc.title}</span>
                    {doc.file_size && <span className="text-xs text-gray-500">({(doc.file_size / 1024).toFixed(1)} KB)</span>}
                  </div>
                  <div className="flex items-center gap-3 mt-1">
                    {doc.ocr_confidence !== null && (
                      <span className={`text-xs px-1.5 py-0.5 rounded ${doc.ocr_confidence >= 0.8 ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                        {Math.round(doc.ocr_confidence * 100)}% {doc.ocr_method === 'google_vision' ? '🌟' : ''}
                      </span>
                    )}
                    {!doc.ocr_processed && <span className="text-xs text-gray-400">لم يُمسح ضوئياً</span>}
                    {doc.ocr_processed && doc.ocr_confidence !== null && doc.ocr_confidence < 0.8 && (
                      <button onClick={() => handleAdvancedScan(doc.id)} disabled={reprocessing === doc.id} className="text-xs text-primary-600 hover:underline">
                        {reprocessing === doc.id ? 'جاري المسح...' : '✨ مسح متقدم'}
                      </button>
                    )}
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  {doc.ocr_confidence !== null && doc.ocr_confidence >= 0.8 && (
                    <button onClick={() => handleAdvancedScan(doc.id)} disabled={reprocessing === doc.id} className="text-xs text-primary-600 hover:underline">
                      {reprocessing === doc.id ? 'جاري...' : '✨ إعادة مسح'}
                    </button>
                  )}
                  <a href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/documents/${doc.id}/download`} className="text-sm text-primary-600 hover:underline">تحميل</a>
                  <button onClick={() => handleDeleteDoc(doc.id)} className="text-sm text-red-500 hover:underline">حذف</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  )
}
