'use client'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'

export default function Navbar() {
  const { user, logout, isLoggedIn } = useAuth()

  return (
    <nav className="bg-white shadow-sm border-b border-gray-100 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link href="/" className="text-2xl font-bold text-primary-700">??????</Link>
        <div className="flex items-center gap-6">
          <Link href="/search" className="text-gray-700 hover:text-primary-600 transition-colors">?????</Link>
          <Link href="/analysis" className="text-gray-700 hover:text-primary-600 transition-colors">???????</Link>
          <Link href="/drafting" className="text-gray-700 hover:text-primary-600 transition-colors">???????</Link>
          <Link href="/lawyers" className="text-gray-700 hover:text-primary-600 transition-colors">????????</Link>
          {isLoggedIn() ? (
            <>
              <Link href="/dashboard" className="text-gray-700 hover:text-primary-600 transition-colors">?????</Link>
              {user?.role === 'admin' && <Link href="/admin" className="text-red-600 hover:text-red-700">???????</Link>}
              <button onClick={logout} className="text-gray-500 hover:text-gray-700">????</button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-gray-700 hover:text-primary-600">????</Link>
              <Link href="/register" className="btn-primary text-sm !py-2 !px-4">?????</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
