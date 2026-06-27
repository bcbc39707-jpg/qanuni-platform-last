'use client'
import Link from 'next/link'
import { useState, useEffect } from 'react'
import { useAuth } from '@/lib/auth'
import api from '@/lib/api'

export default function Navbar() {
  const { user, logout, isLoggedIn } = useAuth()
  const [usage, setUsage] = useState<{ searches_left: number; analyses_left: number; drafts_left: number; advanced_ocr_left: number } | null>(null)

  useEffect(() => {
    if (isLoggedIn()) {
      api.get('/subscriptions/usage').then((res) => setUsage(res.data)).catch(() => {})
    }
  }, [isLoggedIn])

  return (
    <nav className="bg-white shadow-sm border-b border-gray-100 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link href="/" className="text-2xl font-bold text-primary-700">قانوني</Link>
        <div className="flex items-center gap-6">
          <Link href="/search" className="text-gray-700 hover:text-primary-600 transition-colors">بحث</Link>
          <Link href="/analysis" className="text-gray-700 hover:text-primary-600 transition-colors">تحليل</Link>
          <Link href="/drafting" className="text-gray-700 hover:text-primary-600 transition-colors">صياغة</Link>
          <Link href="/documents" className="text-gray-700 hover:text-primary-600 transition-colors">مسح</Link>
          <Link href="/lawyers" className="text-gray-700 hover:text-primary-600 transition-colors">محامون</Link>
          {isLoggedIn() ? (
            <>
              <Link href="/dashboard" className="text-gray-700 hover:text-primary-600 transition-colors">لوحة التحكم</Link>
              {user?.role === 'admin' && <Link href="/admin" className="text-red-600 hover:text-red-700">إدارة</Link>}
              {usage && (
                <span className="text-xs text-gray-500 hidden lg:block">
                  {usage.searches_left} بحث | {usage.analyses_left} تحليل | {usage.drafts_left} صياغة | {usage.advanced_ocr_left} مسح
                </span>
              )}
              <button onClick={logout} className="text-gray-500 hover:text-gray-700">خروج</button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-gray-700 hover:text-primary-600">دخول</Link>
              <Link href="/register" className="btn-primary text-sm !py-2 !px-4">تسجيل</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
