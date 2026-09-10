import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const modules = [
  ["dashboard", "لوحة التحكم", "▦"],
  ["travel", "الحج والعمرة", "🕋"],
  ["pilgrims", "الحجاج والمعتمرون", "👥"],
  ["visas", "التأشيرات", "🪪"],
  ["customers", "العملاء", "◉"],
  ["suppliers", "الموردون", "◇"],
  ["finance", "الصندوق والبنوك والمحافظ", "▣"],
  ["vouchers", "السندات", "▤"],
  ["expenses", "المصروفات", "−"],
  ["accounts", "الحسابات", "≡"],
  ["reports", "التقارير", "▥"],
  ["users", "المستخدمون والصلاحيات", "⚙"],
  ["settings", "الإعدادات", "⚙"],
] as const;

const stats = [
  ["إجمالي المبيعات", "0.00", "ريال يمني"],
  ["المبالغ المحصلة", "0.00", "ريال يمني"],
  ["المستحقات", "0.00", "ريال يمني"],
  ["صافي الربح", "0.00", "ريال يمني"],
];

function App() {
  const [active, setActive] = useState("dashboard");
  const title = modules.find(([id]) => id === active)?.[1] ?? "لوحة التحكم";

  return (
    <div className="shell" dir="rtl">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">م</div>
          <div><strong>نظام المحاسبة</strong><span>وكالة الحج والعمرة</span></div>
        </div>
        <nav>
          {modules.map(([id, label, icon]) => (
            <button key={id} className={active === id ? "nav-item active" : "nav-item"} onClick={() => setActive(id)}>
              <span className="nav-icon">{icon}</span><span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">نسخة مستقلة • جاهزة للتكامل لاحقًا</div>
      </aside>

      <section className="content">
        <header className="topbar">
          <div><h1>{title}</h1><p>نظام إدارة ومحاسبة متكامل لوكالة الحج والعمرة والسفر</p></div>
          <div className="top-actions"><button className="icon-btn">⌕</button><button className="icon-btn">🔔</button><div className="user-chip"><span>م</span><div><b>مدير النظام</b><small>Administrator</small></div></div></div>
        </header>

        {active === "dashboard" ? <Dashboard /> : <ModulePlaceholder title={title} />}
      </section>
    </div>
  );
}

function Dashboard() {
  return <main className="page">
    <div className="welcome"><div><span className="eyebrow">نظرة عامة</span><h2>مرحبًا بك في نظام المحاسبة</h2><p>كل العمليات المالية والتشغيلية للوكالة في مكان واحد.</p></div><button className="primary">＋ عملية جديدة</button></div>
    <div className="stats">{stats.map(([label, value, unit]) => <div className="stat" key={label}><span>{label}</span><strong>{value}</strong><small>{unit}</small></div>)}</div>
    <div className="grid-main">
      <section className="panel"><div className="panel-head"><div><h3>العمليات الأخيرة</h3><p>آخر الحركات المسجلة في النظام</p></div><button className="link">عرض الكل</button></div><div className="empty"><div>▤</div><b>لا توجد عمليات حتى الآن</b><span>ستظهر هنا السندات والحجوزات والمصروفات عند تسجيلها.</span></div></section>
      <section className="panel quick"><div className="panel-head"><div><h3>وصول سريع</h3><p>أهم العمليات اليومية</p></div></div><div className="quick-grid"><Quick label="سند قبض" icon="＋"/><Quick label="سند صرف" icon="−"/><Quick label="حجز عمرة" icon="🕋"/><Quick label="تأشيرة" icon="🪪"/></div></section>
    </div>
    <section className="panel"><div className="panel-head"><div><h3>حالة برامج الحج والعمرة</h3><p>ملخص الطاقة الاستيعابية والحجوزات</p></div></div><div className="program-empty">لا توجد برامج مضافة حاليًا — أضف أول برنامج للبدء.</div></section>
  </main>;
}
function Quick({label, icon}:{label:string;icon:string}) { return <button className="quick-btn"><span>{icon}</span><b>{label}</b><small>إضافة جديد</small></button>; }
function ModulePlaceholder({title}:{title:string}) { return <main className="page"><section className="panel module"><div className="module-icon">▦</div><h2>{title}</h2><p>هذه الوحدة جاهزة ضمن هيكل النظام. سيتم ربطها بواجهة البيانات والعمليات المحاسبية في المرحلة التالية.</p><button className="primary">＋ إضافة جديد</button></section></main>; }

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
