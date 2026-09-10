import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  return (
    <main className="app">
      <header>
        <h1>نظام المحاسبة</h1>
        <p>نظام محاسبي مستقل</p>
      </header>
      <section className="card">
        <h2>لوحة التحكم</h2>
        <p>تم تأسيس الواجهة بنظام RTL. سيتم بناء الوحدات المحاسبية على النواة المزدوجة.</p>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode><App /></React.StrictMode>,
);
