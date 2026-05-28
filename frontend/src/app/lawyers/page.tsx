'use client'
import { useState } from 'react'
import Navbar from '@/components/Navbar'

const mockLawyers = [
  { id: '1', name: '?. ???? ???????', specialization: '????? ????', city: '?????', rating: 4.8, experience: 15 },
  { id: '2', name: '?. ????? ??????', specialization: '????? ?????', city: '???', rating: 4.9, experience: 12 },
  { id: '3', name: '?. ??????? ???????', specialization: '????? ?????', city: '???', rating: 4.7, experience: 20 },
  { id: '4', name: '?. ???? ???????', specialization: '????? ????', city: '?????', rating: 4.6, experience: 8 },
]

export default function LawyersPage() {
  const [search, setSearch] = useState('')
  const filtered = mockLawyers.filter(l => l.name.includes(search) || l.specialization.includes(search) || l.city.includes(search))

  return (
    <>
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 py-10">
        <h1 className="text-3xl font-bold mb-8 text-center">??? ????????</h1>
        <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="???? ?? ????? ?????? ?? ?????? ?? ???????..." className="w-full px-4 py-3 border border-gray-300 rounded-lg mb-8" />
        <div className="grid md:grid-cols-2 gap-4">
          {filtered.map((l) => (
            <div key={l.id} className="card hover:shadow-md transition-shadow">
              <h3 className="text-lg font-bold text-primary-700 mb-1">{l.name}</h3>
              <p className="text-sm text-gray-600 mb-2">{l.specialization} • {l.city}</p>
              <div className="flex justify-between items-center">
                <span className="text-sm text-amber-600">? {l.rating} • {l.experience} ??? ????</span>
                <button className="text-sm bg-primary-100 text-primary-700 px-3 py-1 rounded hover:bg-primary-200">?????</button>
              </div>
            </div>
          ))}
        </div>
      </main>
    </>
  )
}
