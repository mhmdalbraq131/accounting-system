import React, { useEffect, useMemo, useState } from "react";
import { createHajjBooking, createHajjQuota, createPilgrim, getAccounts, getFinancial, getHajjBookings, getHajjQuotas, getParties, getPrograms, postHajjBooking, type Booking, type HajjQuota, type Pilgrim, type Program } from "./api";
import HajjCollectionPanel from "./HajjCollectionPanel";

const money = (v: string | number) => Number(v || 0).toLocaleString("ar-YE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const tabs = [["dashboard", "لوحة الحج"], ["pilgrims", "الحجاج"], ["quotas", "الحصص والموردون"], ["bookings", "الحجوزات والخدمات"], ["collections", "التحصيلات"], ["agents", "الوكلاء"]] as const;

export default function HajjPageTabs({ programs, pilgrims, suppliers, customers }: { programs: Program[]; pilgrims: Pilgrim[]; suppliers: any[]; customers: any[] }) {
  const [tab, setTab] = useState<(typeof tabs)[number][0]>("dashboard");
  const [quotas, setQuotas] = useState<HajjQuota[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState<number | null>(null);
  const [pilgrimForm, setPilgrimForm] = useState({ full_name: "", passport_number: "", nationality: "", phone: "" });
  const [quotaForm, setQuotaForm] = useState({ name_ar: "حصة الحج", season: "", supplier_id: "", total_units: "118", unit_cost: "" });
  const [bookingForm, setBookingForm] = useState({ program_id: "", pilgrim_id: "", quota_id: "", agent_id: "", customer_id: "", party_mode: "agent", sale_price: "", supplier_cost: "" });

  const hajjPrograms = useMemo(() => programs.filter(p => p.program_type === "hajj" && p.is_active), [programs]);
  const selectedQuota = quotas.find(q => q.id === Number(bookingForm.quota_id));

  async function refresh() {
    try {
      const [q, b, a, ac] = await Promise.all([getHajjQuotas(), getHajjBookings(), getParties("agent"), getAccounts()]);
      setQuotas(q); setBookings(b); setAgents(a); setAccounts(ac); setError("");
    } catch (e) { setError(e instanceof Error ? e.message : "تعذر تحميل بيانات الحج"); }
  }
  useEffect(() => { refresh(); }, []);

  async function savePilgrim(e: React.FormEvent) {
    e.preventDefault(); setError(""); setMessage("");
    try { await createPilgrim({ ...pilgrimForm, passport_number: pilgrimForm.passport_number || undefined, nationality: pilgrimForm.nationality || undefined, phone: pilgrimForm.phone || undefined }); setPilgrimForm({ full_name: "", passport_number: "", nationality: "", phone: "" }); setMessage("تم تسجيل الحاج."); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : "تعذر تسجيل الحاج"); }
  }

  async function saveQuota(e: React.FormEvent) {
    e.preventDefault(); setError(""); setMessage("");
    try { await createHajjQuota({ name_ar: quotaForm.name_ar, season: quotaForm.season, supplier_id: Number(quotaForm.supplier_id), total_units: Number(quotaForm.total_units), unit_cost: Number(quotaForm.unit_cost || 0) }); setQuotaForm(v => ({ ...v, season: "", supplier_id: "", unit_cost: "" })); setMessage("تم إنشاء حصة الحج وربطها بالمورد."); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : "تعذر حفظ حصة الحج"); }
  }

  async function saveBooking(e: React.FormEvent) {
    e.preventDefault(); setError(""); setMessage("");
    try {
      const payload: any = { program_id: Number(bookingForm.program_id), pilgrim_id: Number(bookingForm.pilgrim_id), quota_id: Number(bookingForm.quota_id), sale_price: Number(bookingForm.sale_price), supplier_cost: bookingForm.supplier_cost ? Number(bookingForm.supplier_cost) : undefined };
      if (bookingForm.party_mode === "agent") payload.agent_id = Number(bookingForm.agent_id); else payload.customer_id = Number(bookingForm.customer_id);
      await createHajjBooking(payload);
      setBookingForm(v => ({ ...v, pilgrim_id: "", agent_id: "", customer_id: "", sale_price: "", supplier_cost: "" }));
      setMessage("تم تسجيل الخدمة وربط الحاج بالطرف والحصة والمورد."); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "تعذر تسجيل حجز الحج"); }
  }

  async function post(id: number) {
    setBusy(id); setError(""); setMessage("");
    try { await postHajjBooking(id); setMessage(`تم ترحيل خدمة الحج #${id} وإنشاء القيد المحاسبي.`); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : "تعذر ترحيل الخدمة"); }
    finally { setBusy(null); }
  }

  return <main className="page">
    <div className="welcome"><div><span className="eyebrow">قسم الحج</span><h2>إدارة الحج</h2><p>كل وظيفة في تبويب مستقل: الحجاج، الحصص، الحجوزات، التحصيلات والوكلاء.</p></div></div>
    {(error || message) && <div className={error ? "error-banner" : "notice-banner"}>{error || message}</div>}
    <div className="quick-grid" style={{ marginBottom: 20 }}>{tabs.map(([id, label]) => <button key={id} className={tab === id ? "quick-btn active" : "quick-btn"} onClick={() => { setTab(id); setError(""); setMessage(""); }}><b>{label}</b><small>فتح</small></button>)}</div>

    {tab === "dashboard" && <>
      <div className="stats compact">
        <div className="stat"><span>إجمالي الحصة</span><strong>{quotas.reduce((n, q) => n + q.total_units, 0)}</strong><small>حاج</small></div>
        <div className="stat"><span>المستخدم</span><strong>{quotas.reduce((n, q) => n + q.used_units, 0)}</strong><small>حاج</small></div>
        <div className="stat"><span>المتبقي</span><strong>{quotas.reduce((n, q) => n + q.remaining_units, 0)}</strong><small>حاج</small></div>
        <div className="stat"><span>الخدمات</span><strong>{bookings.length}</strong><small>حجز</small></div>
      </div>
      <section className="panel"><div className="panel-head"><div><h3>مسار العمل</h3><p>سجل الحاج، أنشئ حصة مرتبطة بالمورد، اربط الخدمة بالوكيل أو العميل، ثم رحّلها والتحصيل يكون من تبويب التحصيلات.</p></div></div></section>
    </>}

    {tab === "pilgrims" && <section className="panel"><div className="panel-head"><div><h3>تسجيل الحجاج</h3><p>بيانات الحاج الأساسية مستقلة عن الحجز ويمكن إعادة استخدامها مع خدمات أخرى.</p></div></div><form className="form-grid" onSubmit={savePilgrim}><label><span>الاسم الكامل</span><input value={pilgrimForm.full_name} onChange={e => setPilgrimForm({ ...pilgrimForm, full_name: e.target.value })} required /></label><label><span>رقم الجواز</span><input value={pilgrimForm.passport_number} onChange={e => setPilgrimForm({ ...pilgrimForm, passport_number: e.target.value })} /></label><label><span>الجنسية</span><input value={pilgrimForm.nationality} onChange={e => setPilgrimForm({ ...pilgrimForm, nationality: e.target.value })} /></label><label><span>الهاتف</span><input value={pilgrimForm.phone} onChange={e => setPilgrimForm({ ...pilgrimForm, phone: e.target.value })} /></label><div className="form-actions"><button className="primary">حفظ الحاج</button></div></form><div className="table-wrap" style={{ marginTop: 20 }}><table><thead><tr><th>الاسم</th><th>الجواز</th><th>الجنسية</th><th>الهاتف</th><th>الحالة</th></tr></thead><tbody>{pilgrims.map(p => <tr key={p.id}><td>{p.full_name}</td><td>{p.passport_number || "—"}</td><td>{p.nationality || "—"}</td><td>{p.phone || "—"}</td><td>{p.visa_status}</td></tr>)}</tbody></table></div></section>}

    {tab === "quotas" && <section className="panel"><div className="panel-head"><div><h3>حصص الحج والموردون</h3><p>كل حصة تمثل مصدرًا للمقاعد والتكلفة، ويمكن فتح حصة جديدة من مورد أو وكالة أخرى عند انتهاء الحصة السابقة.</p></div></div><form className="form-grid" onSubmit={saveQuota}><label><span>اسم الحصة</span><input value={quotaForm.name_ar} onChange={e => setQuotaForm({ ...quotaForm, name_ar: e.target.value })} required /></label><label><span>الموسم</span><input value={quotaForm.season} onChange={e => setQuotaForm({ ...quotaForm, season: e.target.value })} placeholder="1448هـ" required /></label><label><span>المورد</span><select value={quotaForm.supplier_id} onChange={e => setQuotaForm({ ...quotaForm, supplier_id: e.target.value })} required><option value="">اختر المورد...</option>{suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label><label><span>عدد المقاعد</span><input type="number" min="1" value={quotaForm.total_units} onChange={e => setQuotaForm({ ...quotaForm, total_units: e.target.value })} required /></label><label><span>تكلفة المقعد</span><input type="number" min="0" step="0.01" value={quotaForm.unit_cost} onChange={e => setQuotaForm({ ...quotaForm, unit_cost: e.target.value })} required /></label><div className="form-actions"><button className="primary">حفظ الحصة</button></div></form><div className="table-wrap" style={{ marginTop: 20 }}><table><thead><tr><th>الحصة</th><th>الموسم</th><th>المقاعد</th><th>المستخدم</th><th>المتبقي</th><th>التكلفة</th><th>الحالة</th></tr></thead><tbody>{quotas.map(q => <tr key={q.id}><td>{q.name_ar}</td><td>{q.season}</td><td>{q.total_units}</td><td>{q.used_units}</td><td>{q.remaining_units}</td><td>{money(q.unit_cost)}</td><td>{q.status}</td></tr>)}</tbody></table></div></section>}

    {tab === "bookings" && <>
      <section className="panel"><div className="panel-head"><div><h3>تسجيل خدمة حج</h3><p>الخدمة تربط الحاج بالطرف المالي والحصة التي تحدد المورد والتكلفة.</p></div></div><form className="form-grid" onSubmit={saveBooking}><label><span>برنامج الحج</span><select value={bookingForm.program_id} onChange={e => setBookingForm({ ...bookingForm, program_id: e.target.value })} required><option value="">اختر البرنامج...</option>{hajjPrograms.map(p => <option key={p.id} value={p.id}>{p.code} - {p.name_ar}</option>)}</select></label><label><span>الحاج</span><select value={bookingForm.pilgrim_id} onChange={e => setBookingForm({ ...bookingForm, pilgrim_id: e.target.value })} required><option value="">اختر الحاج...</option>{pilgrims.map(p => <option key={p.id} value={p.id}>{p.full_name} — {p.passport_number || "بدون جواز"}</option>)}</select></label><label><span>الحصة / المورد</span><select value={bookingForm.quota_id} onChange={e => { const q = quotas.find(x => x.id === Number(e.target.value)); setBookingForm({ ...bookingForm, quota_id: e.target.value, supplier_cost: q ? String(q.unit_cost) : "" }); }} required><option value="">اختر الحصة...</option>{quotas.filter(q => q.remaining_units > 0).map(q => <option key={q.id} value={q.id}>{q.name_ar} — المتبقي {q.remaining_units}</option>)}</select></label><label><span>الطرف</span><select value={bookingForm.party_mode} onChange={e => setBookingForm({ ...bookingForm, party_mode: e.target.value, agent_id: "", customer_id: "" })}><option value="agent">وكيل</option><option value="customer">عميل مباشر</option></select></label>{bookingForm.party_mode === "agent" ? <label><span>الوكيل</span><select value={bookingForm.agent_id} onChange={e => setBookingForm({ ...bookingForm, agent_id: e.target.value })} required><option value="">اختر الوكيل...</option>{agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label> : <label><span>العميل</span><select value={bookingForm.customer_id} onChange={e => setBookingForm({ ...bookingForm, customer_id: e.target.value })} required><option value="">اختر العميل...</option>{customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>}<label><span>سعر البيع</span><input type="number" min="0.01" step="0.01" value={bookingForm.sale_price} onChange={e => setBookingForm({ ...bookingForm, sale_price: e.target.value })} required /></label><label><span>تكلفة المورد</span><input type="number" min="0" step="0.01" value={bookingForm.supplier_cost} onChange={e => setBookingForm({ ...bookingForm, supplier_cost: e.target.value })} placeholder={selectedQuota ? String(selectedQuota.unit_cost) : ""} /></label><div className="form-actions"><button className="primary">حفظ الخدمة</button></div></form></section>
      <section className="panel"><div className="panel-head"><div><h3>سجل خدمات الحج</h3><p>الخدمة المرحّلة لا تعدل؛ الإلغاء يعكس أثرها المحاسبي.</p></div></div><div className="table-wrap"><table><thead><tr><th>رقم الخدمة</th><th>الحاج</th><th>الطرف</th><th>البيع</th><th>التكلفة</th><th>المدفوع</th><th>المتبقي</th><th>الربح</th><th>الحالة</th><th>إجراء</th></tr></thead><tbody>{bookings.map(r => <tr key={r.id}><td>#{r.id}</td><td>{pilgrims.find(p => p.id === r.pilgrim_id)?.full_name || `حاج #${r.pilgrim_id}`}</td><td>{r.agent_id ? agents.find(a => a.id === r.agent_id)?.name || `وكيل #${r.agent_id}` : customers.find(c => c.id === r.customer_id)?.name || `عميل #${r.customer_id}`}</td><td>{money(r.sale_price)}</td><td>{money(r.supplier_cost)}</td><td>{money(r.paid_amount)}</td><td>{money(r.remaining_amount)}</td><td>{money(r.profit)}</td><td>{r.status === "draft" ? "مسودة" : r.status === "confirmed" ? "مؤكد" : r.status === "posted" ? "مرحّل" : r.status}</td><td>{r.status === "draft" || r.status === "confirmed" ? <button className="link" disabled={busy === r.id} onClick={() => post(r.id)}>{busy === r.id ? "جارٍ…" : "ترحيل"}</button> : "—"}</td></tr>)}</tbody></table></div></section>
    </>}

    {tab === "collections" && <HajjCollectionPanel />}

    {tab === "agents" && <section className="panel"><div className="panel-head"><div><h3>الوكلاء</h3><p>الوكيل طرف مالي مرتبط بحساب محاسبي. إنشاء الموردين والأطراف المحاسبية يتم من الدليل المحاسبي، ثم تستخدم هنا في الخدمات.</p></div></div><div className="table-wrap"><table><thead><tr><th>الوكيل</th><th>الرمز</th><th>الهاتف</th><th>الحساب</th><th>الحالة</th></tr></thead><tbody>{agents.map(a => <tr key={a.id}><td>{a.name}</td><td>{a.code || "—"}</td><td>{a.phone || "—"}</td><td>{accounts.find(x => x.id === a.account_id)?.code || a.account_id || "غير مربوط"}</td><td>{a.is_active ? "نشط" : "موقوف"}</td></tr>)}</tbody></table></div></section>}
  </main>;
}
