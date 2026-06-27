'use client'
import Link from 'next/link'

const sections = [
  { href: '/admin/users', title: 'إدارة المستخدمين', desc: 'عرض وإدارة حسابات المستخدمين', icon: '👥', color: 'border-red-200 hover:bg-red-50' },
  { href: '/admin/content', title: 'إدارة المحتوى', desc: 'إدارة القوانين والأحكام والمستندات', icon: '📚', color: 'border-blue-200 hover:bg-blue-50' },
  { href: '/admin/cases', title: 'إدارة القضايا', desc: 'عرض وإدارة القضايا المرفوعة', icon: '⚖️', color: 'border-amber-200 hover:bg-amber-50' },
  { href: '/admin/index', title: 'إدارة الفهارس', desc: 'إدارة فهارس البحث', icon: '🔍', color: 'border-green-200 hover:bg-green-50' },
  { href: '/admin/rag', title: 'إدارة RAG', desc: 'إدارة قاعدة المعرفة القانونية', icon: '🧠', color: 'border-purple-200 hover:bg-purple-50' },
  { href: '/admin/subscriptions', title: 'إدارة الاشتراكات', desc: 'عرض خطط الاشتراكات والإحصائيات', icon: '💳', color: 'border-teal-200 hover:bg-teal-50' },
  { href: '/admin/upload', title: 'رفع قانون (PDF)', desc: 'رفع ملف PDF واستخراج هيكله القانوني تلقائياً', icon: '📤', color: 'border-indigo-200 hover:bg-indigo-50' },
]

export default function AdminPage() {
  return (
    <main className="max-w-6xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-8 text-red-700">لوحة الإدارة</h1>
      <div className="grid md:grid-cols-3 gap-6">
        {sections.map((s) => (
          <Link key={s.href} href={s.href} className={`card border-2 ${s.color} transition-all hover:shadow-md`}>
            <div className="text-3xl mb-3">{s.icon}</div>
            <h3 className="font-bold mb-2">{s.title}</h3>
            <p className="text-gray-600 text-sm">{s.desc}</p>
          </Link>
        ))}
      </div>
    </main>
  )
}
