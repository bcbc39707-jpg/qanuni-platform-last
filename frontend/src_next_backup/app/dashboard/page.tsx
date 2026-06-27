'use client'
import { useState, useEffect } from 'react'
import api from '@/lib/api'
import Link from 'next/link'

interface Usage {
  searches_left: number; analyses_left: number; drafts_left: number; advanced_ocr_left: number
  searches_quota: number; analyses_quota: number; drafts_quota: number; advanced_ocr_quota: number
}

export default function DashboardPage() {
  const [cases, setCases] = useState<any[]>([])
  const [usage, setUsage] = useState<Usage | null>(null)

  useEffect(() => {
    api.get('/cases').then(res => setCases(res.data)).catch(() => {})
    api.get('/subscriptions/usage').then(res => setUsage(res.data)).catch(() => {})
  }, [])

  return (
    <>
      <main className="max-w-6xl mx-auto px-4 py-10">
        <h1 className="text-3xl font-bold mb-8">لوحة التحكم</h1>

        <div className="grid md:grid-cols-4 gap-4 mb-10">
          <div className="card text-center"><div className="text-3xl font-bold text-primary-600">{cases.length}</div><div className="text-gray-600 text-sm">قضايا</div></div>
          <div className="card text-center"><div className="text-3xl font-bold text-green-600">{usage ? usage.searches_quota - usage.searches_left : 0}</div><div className="text-gray-600 text-sm">بحث مستخدم</div></div>
          <div className="card text-center"><div className="text-3xl font-bold text-amber-600">{usage ? usage.analyses_quota - usage.analyses_left : 0}</div><div className="text-gray-600 text-sm">تحليل مستخدم</div></div>
          <div className="card text-center"><div className="text-3xl font-bold text-purple-600">0</div><div className="text-gray-600 text-sm">مستندات</div></div>
        </div>

        {usage && (
          <div className="grid md:grid-cols-4 gap-4 mb-10">
            <div className="card">
              <h3 className="font-bold mb-2">البحث القانوني</h3>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div className="bg-primary-600 h-2.5 rounded-full" style={{ width: `${Math.min(100, (usage.searches_quota > 0 ? ((usage.searches_quota - usage.searches_left) / usage.searches_quota) * 100 : 0))}%` }} />
              </div>
              <p className="text-sm text-gray-500 mt-1">{usage.searches_left} / {usage.searches_quota} متبقي</p>
            </div>
            <div className="card">
              <h3 className="font-bold mb-2">التحليل الذكي</h3>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div className="bg-amber-500 h-2.5 rounded-full" style={{ width: `${Math.min(100, (usage.analyses_quota > 0 ? ((usage.analyses_quota - usage.analyses_left) / usage.analyses_quota) * 100 : 0))}%` }} />
              </div>
              <p className="text-sm text-gray-500 mt-1">{usage.analyses_left} / {usage.analyses_quota} متبقي</p>
            </div>
            <div className="card">
              <h3 className="font-bold mb-2">الصياغة القانونية</h3>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div className="bg-green-500 h-2.5 rounded-full" style={{ width: `${Math.min(100, (usage.drafts_quota > 0 ? ((usage.drafts_quota - usage.drafts_left) / usage.drafts_quota) * 100 : 0))}%` }} />
              </div>
              <p className="text-sm text-gray-500 mt-1">{usage.drafts_left} / {usage.drafts_quota} متبقي</p>
            </div>
            <div className="card">
              <h3 className="font-bold mb-2">المسح المتقدم</h3>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div className="bg-purple-500 h-2.5 rounded-full" style={{ width: `${Math.min(100, (usage.advanced_ocr_quota > 0 ? ((usage.advanced_ocr_quota - usage.advanced_ocr_left) / usage.advanced_ocr_quota) * 100 : 0))}%` }} />
              </div>
              <p className="text-sm text-gray-500 mt-1">{usage.advanced_ocr_left} / {usage.advanced_ocr_quota} متبقي</p>
            </div>
          </div>
        )}

        <div className="grid md:grid-cols-4 gap-4 mb-10">
          <Link href="/search" className="card hover:shadow-md transition-shadow text-center"><div className="text-2xl mb-2">🔍</div><div className="font-bold">بحث قانوني</div></Link>
          <Link href="/analysis" className="card hover:shadow-md transition-shadow text-center"><div className="text-2xl mb-2">⚖️</div><div className="font-bold">تحليل ذكي</div></Link>
          <Link href="/drafting" className="card hover:shadow-md transition-shadow text-center"><div className="text-2xl mb-2">📝</div><div className="font-bold">صياغة قانونية</div></Link>
          <Link href="/documents" className="card hover:shadow-md transition-shadow text-center"><div className="text-2xl mb-2">📄</div><div className="font-bold">مسح مستندات</div></Link>
        </div>

        <h2 className="text-xl font-bold mb-4">آخر القضايا</h2>
        {cases.length === 0 ? (
          <p className="text-gray-500">لا توجد قضايا بعد.</p>
        ) : (
          <div className="space-y-3">
            {cases.map((c: any) => (
              <Link href={`/cases/${c.id}`} key={c.id} className="card flex justify-between items-center hover:shadow-md transition-shadow">
                <div><div className="font-bold">{c.title}</div><div className="text-sm text-gray-500">{c.case_type}</div></div>
                <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700">{c.status}</span>
              </Link>
            ))}
          </div>
        )}
      </main>
    </>
  )
}
