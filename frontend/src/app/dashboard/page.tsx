'use client'
import { useState, useEffect } from 'react'
import Navbar from '@/components/Navbar'
import api from '@/lib/api'
import Link from 'next/link'

export default function DashboardPage() {
  const [cases, setCases] = useState<any[]>([])

  useEffect(() => {
    api.get('/cases').then(res => setCases(res.data)).catch(() => {})
  }, [])

  return (
    <>
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-10">
        <h1 className="text-3xl font-bold mb-8">???? ??????</h1>

        <div className="grid md:grid-cols-4 gap-4 mb-10">
          <div className="card text-center"><div className="text-3xl font-bold text-primary-600">{cases.length}</div><div className="text-gray-600 text-sm">??????</div></div>
          <div className="card text-center"><div className="text-3xl font-bold text-green-600">0</div><div className="text-gray-600 text-sm">?????</div></div>
          <div className="card text-center"><div className="text-3xl font-bold text-amber-600">0</div><div className="text-gray-600 text-sm">???????</div></div>
          <div className="card text-center"><div className="text-3xl font-bold text-purple-600">0</div><div className="text-gray-600 text-sm">??????</div></div>
        </div>

        <div className="grid md:grid-cols-3 gap-4 mb-10">
          <Link href="/search" className="card hover:shadow-md transition-shadow text-center"><div className="text-2xl mb-2">??</div><div className="font-bold">??? ??????</div></Link>
          <Link href="/analysis" className="card hover:shadow-md transition-shadow text-center"><div className="text-2xl mb-2">??</div><div className="font-bold">????? ???</div></Link>
          <Link href="/drafting" className="card hover:shadow-md transition-shadow text-center"><div className="text-2xl mb-2">??</div><div className="font-bold">????? ?????</div></Link>
        </div>

        <h2 className="text-xl font-bold mb-4">?????? ???????</h2>
        {cases.length === 0 ? (
          <p className="text-gray-500">?? ???? ????? ???.</p>
        ) : (
          <div className="space-y-3">
            {cases.map((c) => (
              <div key={c.id} className="card flex justify-between items-center">
                <div><div className="font-bold">{c.title}</div><div className="text-sm text-gray-500">{c.case_type}</div></div>
                <span className={	ext-xs px-2 py-1 rounded }>{c.status}</span>
              </div>
            ))}
          </div>
        )}
      </main>
    </>
  )
}
