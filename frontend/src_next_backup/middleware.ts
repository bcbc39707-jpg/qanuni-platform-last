import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const protectedRoutes = ['/dashboard', '/cases', '/analysis', '/drafting', '/admin', '/subscribe', '/documents']

export function middleware(request: NextRequest) {
  const token = request.cookies.get('token')?.value
  const path = request.nextUrl.pathname

  const isProtected = protectedRoutes.some(route => path.startsWith(route))
  const isAuthPage = path === '/login' || path === '/register'

  if (isProtected && !token) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', path)
    return NextResponse.redirect(loginUrl)
  }

  if (isAuthPage && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*', '/cases/:path*', '/analysis/:path*', '/drafting/:path*', '/admin/:path*', '/subscribe/:path*', '/login', '/register'],
}
