'use client'
const plans = [
  { name: 'مجاني', price: 'مجاناً', features: ['بحث محدود (10/شهر)', 'دعم أساسي', 'حساب واحد'], cta: 'اشتراك مجاني', highlight: false },
  { name: 'احترافي', price: '29$/شهر', features: ['بحث غير محدود', 'تحليل ذكي (50/شهر)', 'صياغة قانونية (20/شهر)', 'مسح مستندات', 'دعم OCR'], cta: 'اشتراك الآن', highlight: true },
  { name: 'مؤسسي', price: '99$/شهر', features: ['كل المميزات السابقة', 'تحليل غير محدود', 'صياغة غير محدودة', 'API Access', 'دعم فوري', 'تقارير متقدمة'], cta: 'تواصل معنا', highlight: false },
]

export default function SubscribePage() {
  return (
    <>
      <main className="max-w-5xl mx-auto px-4 py-16">
        <h1 className="text-3xl font-bold text-center mb-4">خطط الاشتراك</h1>
        <p className="text-center text-gray-600 mb-12">اختر الخطة المناسبة لاحتياجاتك القانونية</p>
        <div className="grid md:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <div key={plan.name} className={`card text-center ${plan.highlight ? 'border-primary-500 border-2' : ''}`}>
              {plan.highlight && <div className="text-xs bg-primary-600 text-white px-3 py-1 rounded-full inline-block mb-3">الأكثر شعبية</div>}
              <h3 className="text-xl font-bold mb-2">{plan.name}</h3>
              <div className="text-3xl font-bold text-primary-700 mb-4">{plan.price}</div>
              <ul className="text-sm text-gray-600 space-y-2 mb-6 text-right">
                {plan.features.map((f, i) => <li key={i}>✓ {f}</li>)}
              </ul>
              <button className={plan.highlight ? 'btn-primary w-full' : 'btn-secondary w-full'}>{plan.cta}</button>
            </div>
          ))}
        </div>
      </main>
    </>
  )
}
