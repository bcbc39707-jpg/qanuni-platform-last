'use client'
import { useState, useEffect } from 'react'
import Navbar from '@/components/Navbar'
import api from '@/lib/api'

export default function CasesPage() {
  const [cases, setCases] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ title: '', case_type: 'civil', description: '', court_name: '' })

  useEffect(() => { api.get('/cases').then(r => setCases(r.data)).catch(() => {}) }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const res = await api.post('/cases', form)
      setCases([res.data, ...cases])
      setShowForm(false)
      setForm({ title: '', case_type: 'civil', description: '', court_name: '' })
    } catch {}
  }

  return (
    <>
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 py-10">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">??????</h1>
          <button onClick={() => setShowForm(!showForm)} className="btn-primary">+ ???? ?????</button>
        </div>

        {showForm && (
          <form onSubmit={handleCreate} className="card mb-6 space-y-3">
            <input type="text" value={form.title} onChange={(e) => setForm({...form, title: e.target.value})} placeholder="????? ??????" className="w-full px-4 py-2 border rounded-lg" required />
            <select value={form.case_type} onChange={(e) => setForm({...form, case_type: e.target.value})} className="w-full px-4 py-2 border rounded-lg">
              <option value="civil">????</option><option value="criminal">?????</option><option value="commercial">?????</option><option value="family">????? ?????</option><option value="labor">?????</option><option value="administrative">?????</option>
            </select>
            <textarea value={form.description} onChange={(e) => setForm({...form, description: e.target.value})} placeholder="??? ??????" className="w-full px-4 py-2 border rounded-lg h-24 resize-none" />
            <button type="submit" className="btn-primary">?????</button>
          </form>
        )}

        <div className="space-y-3">
          {cases.map((c) => (
            <div key={c.id} className="card flex justify-between items-center">
              <div><div className="font-bold">{c.title}</div><div className="text-sm text-gray-500">{c.case_type}</div></div>
              <span className="text-xs px-2 py-1 rounded bg-green-100 text-green-700">{c.status}</span>
            </div>
          ))}
          {cases.length === 0 && <p className="text-gray-500 text-center">?? ???? ?????. ???? ??? ????!</p>}
        </div>
      </main>
    </>
  )
}
