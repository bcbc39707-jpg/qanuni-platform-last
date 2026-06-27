'use client'
import { useState, useEffect, useRef } from 'react'
import api from '@/lib/api'

export default function DocumentsPage() {
  const [docs, setDocs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [ocrText, setOcrText] = useState('')
  const [showOcr, setShowOcr] = useState(false)
  const [uploadMsg, setUploadMsg] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const fetchDocs = async () => {
    setLoading(true)
    try {
      const res = await api.get('/documents')
      setDocs(res.data)
    } catch { } finally { setLoading(false) }
  }

  useEffect(() => { fetchDocs() }, [])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadMsg('')
    setOcrText('')
    setShowOcr(false)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('title', file.name)
      const res = await api.post('/documents/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      setUploadMsg(`تم رفع الملف بنجاح`)
      if (res.data.ocr_processed) {
        setShowOcr(true)
        setOcrText(await fetchDocContent(res.data.id))
      }
      fetchDocs()
    } catch (err: any) {
      setUploadMsg(err.response?.data?.detail || 'فشل الرفع')
    } finally { setUploading(false); if (fileRef.current) fileRef.current.value = '' }
  }

  const fetchDocContent = async (id: string) => {
    try {
      const res = await api.get(`/documents/${id}`)
      return res.data.content || ''
    } catch { return '' }
  }

  const handleAdvancedOcr = async (id: string) => {
    try {
      const res = await api.post(`/documents/${id}/reprocess-advanced`)
      setOcrText(res.data.ocr_processed ? 'تمت إعادة المسح المتقدم بنجاح' : '')
      fetchDocs()
    } catch (err: any) {
      setUploadMsg(err.response?.data?.detail || 'فشل المسح المتقدم')
    }
  }

  const downloadDoc = async (id: string, title: string) => {
    try {
      const res = await api.get(`/documents/${id}/download`, { responseType: 'blob' })
      const url = URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url; a.download = title; a.click()
      URL.revokeObjectURL(url)
    } catch { }
  }

  const deleteDoc = async (id: string) => {
    if (!confirm('حذف المستند؟')) return
    try { await api.delete(`/documents/${id}`); fetchDocs() } catch { }
  }

  const formatSize = (bytes: number) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <main className="max-w-5xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-8 text-center">المستندات والمسح الضوئي</h1>

      <div className="card mb-8">
        <h3 className="font-bold text-lg mb-4">رفع مستند جديد</h3>
        <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png,.docx,.tif,.tiff" onChange={handleUpload}
          className="w-full px-4 py-8 border-2 border-dashed border-gray-300 rounded-lg text-center cursor-pointer hover:border-primary-400" />
        {uploading && <p className="text-center text-gray-500 mt-2">جاري الرفع والمعالجة...</p>}
        {uploadMsg && <p className="text-center text-sm mt-2 text-green-600">{uploadMsg}</p>}
      </div>

      {showOcr && ocrText && (
        <div className="card mb-8">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-bold text-primary-700">النص المستخرج من المسح الضوئي</h3>
            <button onClick={() => { navigator.clipboard.writeText(ocrText); setUploadMsg('تم النسخ') }} className="text-sm text-primary-600 hover:underline">نسخ</button>
          </div>
          <div className="whitespace-pre-wrap text-gray-700 leading-relaxed max-h-60 overflow-y-auto bg-gray-50 p-4 rounded-lg text-sm">{ocrText}</div>
        </div>
      )}

      <h2 className="text-xl font-bold mb-4">المستندات السابقة</h2>
      {loading ? <p className="text-gray-500">جاري التحميل...</p> : (
        <div className="space-y-3">
          {docs.map((d) => (
            <div key={d.id} className="card flex justify-between items-center">
              <div className="flex-1">
                <div className="font-bold">{d.title}</div>
                <div className="text-sm text-gray-500 mt-1">
                  <span className="text-xs bg-gray-100 px-2 py-0.5 rounded ml-2">{d.doc_type}</span>
                  {d.file_size && <span>{formatSize(d.file_size)}</span>}
                  {d.ocr_processed && <span className="mr-2 text-green-600">✓ OCR</span>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => downloadDoc(d.id, d.title)} className="text-xs px-2 py-1 rounded border hover:bg-gray-100">تنزيل</button>
                <button onClick={() => handleAdvancedOcr(d.id)} className="text-xs px-2 py-1 rounded border border-amber-200 text-amber-700 hover:bg-amber-50">مسح متقدم</button>
                <button onClick={() => deleteDoc(d.id)} className="text-xs px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50">حذف</button>
              </div>
            </div>
          ))}
          {docs.length === 0 && <p className="text-gray-500 text-center">لا توجد مستندات مرفوعة</p>}
        </div>
      )}
    </main>
  )
}
