import Link from 'next/link'

export default function Home() {
  return (
    <main className="min-h-screen">
      <section className="bg-gradient-to-bl from-primary-900 via-primary-700 to-primary-600 text-white">
        <div className="max-w-7xl mx-auto px-4 py-20 text-center">
          <h1 className="text-5xl font-bold mb-6">قانوني</h1>
          <p className="text-xl text-blue-100 mb-4">منصة قانونية يمنية شاملة تعمل بالذكاء الاصطناعي</p>
          <p className="text-lg text-blue-200 mb-10 max-w-2xl mx-auto">أول منصة يمنية • محرك بحث قانوني ذكي • صياغة المستندات القانونية</p>
          <div className="flex gap-4 justify-center">
            <Link href="/search" className="btn-primary text-lg">ابدأ البحث القانوني</Link>
            <Link href="/register" className="btn-secondary text-lg !text-white !border-white/30 hover:!bg-white/10">إنشاء حساب</Link>
          </div>
        </div>
      </section>
      <section className="max-w-7xl mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-center mb-12">مميزاتنا</h2>
        <div className="grid md:grid-cols-3 gap-8">
          <Link href="/search" className="card text-center hover:shadow-md transition-shadow"><div className="text-4xl mb-4">📚</div><h3 className="text-xl font-bold mb-2">مكتبة قانونية ضخمة</h3><p className="text-gray-600">آلاف القوانين والأحكام والمستندات القانونية</p></Link>
          <Link href="/search" className="card text-center hover:shadow-md transition-shadow"><div className="text-4xl mb-4">🔍</div><h3 className="text-xl font-bold mb-2">بحث ذكي بالذكاء الاصطناعي</h3><p className="text-gray-600">ابحث عن أي معلومة قانونية بدقة وسرعة</p></Link>
          <Link href="/drafting" className="card text-center hover:shadow-md transition-shadow"><div className="text-4xl mb-4">📝</div><h3 className="text-xl font-bold mb-2">صياغة قانونية</h3><p className="text-gray-600">صياغة مستندات قانونية احترافية بالذكاء الاصطناعي</p></Link>
          <Link href="/analysis" className="card text-center hover:shadow-md transition-shadow"><div className="text-4xl mb-4">⚖️</div><h3 className="text-xl font-bold mb-2">تحليل القضايا</h3><p className="text-gray-600">تحليل متكامل للقضايا مع التوصيات القانونية</p></Link>
          <Link href="/documents" className="card text-center hover:shadow-md transition-shadow"><div className="text-4xl mb-4">📄</div><h3 className="text-xl font-bold mb-2">مسح المستندات</h3><p className="text-gray-600">تعرف ضوئي على النصوص العربية من المستندات</p></Link>
          <Link href="/analysis" className="card text-center hover:shadow-md transition-shadow"><div className="text-4xl mb-4">🤖</div><h3 className="text-xl font-bold mb-2">ذكاء اصطناعي</h3><p className="text-gray-600">مدعوم بـ GPT-4 لأدق النتائج القانونية</p></Link>
        </div>
      </section>
    </main>
  )
}
