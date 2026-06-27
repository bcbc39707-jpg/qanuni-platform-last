import type { Metadata } from 'next'
import './globals.css'
import AuthProvider from '@/components/AuthProvider'
import Navbar from '@/components/Navbar'

export const metadata: Metadata = {
  title: 'قانوني | منصة قانونية يمنية شاملة',
  description: 'منصة قانونية ذكية تعمل بالذكاء الاصطناعي - أول منصة يمنية متكاملة للبحث القانوني',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;800&display=swap" rel="stylesheet" />
      </head>
      <body className="font-arabic bg-gray-50 text-gray-900 antialiased">
        <AuthProvider>
          <Navbar />
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
