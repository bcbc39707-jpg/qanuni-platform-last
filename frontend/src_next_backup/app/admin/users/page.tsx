'use client'
import { useState, useEffect } from 'react'
import api from '@/lib/api'

export default function AdminUsersPage() {
  const [users, setUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const res = await api.get('/admin/users')
      setUsers(res.data)
    } catch { } finally { setLoading(false) }
  }

  useEffect(() => { fetchUsers() }, [])

  const changeRole = async (id: string, role: string) => {
    try { await api.put(`/admin/users/${id}/role`, { role }); fetchUsers() } catch { }
  }

  const toggleStatus = async (id: string, isActive: boolean) => {
    try { await api.put(`/admin/users/${id}/status`, { is_active: !isActive }); fetchUsers() } catch { }
  }

  const deleteUser = async (id: string) => {
    if (!confirm('هل أنت متأكد من حذف هذا المستخدم؟')) return
    try { await api.delete(`/admin/users/${id}`); fetchUsers() } catch { }
  }

  const roleColors: Record<string, string> = { admin: 'bg-red-100 text-red-700', reviewer: 'bg-purple-100 text-purple-700', lawyer: 'bg-blue-100 text-blue-700', client: 'bg-green-100 text-green-700' }
  const roleLabels: Record<string, string> = { admin: 'مدير', reviewer: 'مراجع', lawyer: 'محامٍ', client: 'عميل' }

  if (loading) return <main className="max-w-6xl mx-auto px-4 py-10"><p>جاري التحميل...</p></main>

  return (
    <main className="max-w-6xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-8 text-red-700">إدارة المستخدمين</h1>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-100 text-right">
              <th className="p-3">الاسم</th><th className="p-3">البريد</th><th className="p-3">الدور</th><th className="p-3">الحالة</th><th className="p-3">الإجراءات</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b hover:bg-gray-50">
                <td className="p-3 font-medium">{u.full_name}</td>
                <td className="p-3 text-gray-600">{u.email}</td>
                <td className="p-3">
                  <select value={u.role} onChange={(e) => changeRole(u.id, e.target.value)} className="text-sm border rounded px-2 py-1">
                    {Object.entries(roleLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </td>
                <td className="p-3">
                  <span className={`text-xs px-2 py-1 rounded ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{u.is_active ? 'نشط' : 'موقوف'}</span>
                </td>
                <td className="p-3 flex gap-2">
                  <button onClick={() => toggleStatus(u.id, u.is_active)} className="text-xs px-2 py-1 rounded border hover:bg-gray-100">{u.is_active ? 'إيقاف' : 'تفعيل'}</button>
                  <button onClick={() => deleteUser(u.id)} className="text-xs px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50">حذف</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  )
}
