import React, { useEffect, useMemo, useState } from "react";
import {
  createHajjBooking,
  createHajjQuota,
  getHajjBookings,
  getHajjQuotas,
  getParties,
  postHajjBooking,
  type HajjQuota,
  type Booking,
  type Program,
  type Pilgrim,
} from "./api";

const money = (v: string | number) => Number(v || 0).toLocaleString("ar-YE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function HajjPage({ programs, pilgrims, suppliers, customers }: { programs: Program[]; pilgrims: Pilgrim[]; suppliers: any[]; customers: any[] }) {
  const [quotas, setQuotas] = useState<HajjQuota[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [quotaForm, setQuotaForm] = useState({ name_ar: "حصة الحج", season: "", supplier_id: "", total_units: "118", unit_cost: "" });
  const [bookingForm, setBookingForm] = useState({ program_id: "", pilgrim_id: "", quota_id: "", party_mode: "agent", agent_id: "", customer_id: "", sale_price: "", supplier_cost: "" });
  const hajjPrograms = useMemo(() => programs.filter(p => p.program_type === "hajj" && p.is_active), [programs]);
  const selectedQuota = quotas.find(q => q.id === Number(bookingForm.quota_id));

  async function refresh() {
    try {
      const [q, b, a] = await Promise.all([getHajjQuotas(), getHajjBookings(), getParties("agent")]);
      setQuotas(q); setBookings(b); setAgents(a); setError("");
    } catch (e) { setError(e instanceof Error ? e.message : "تعذر تحميل بيانات الحج"); }
  }
  useEffect(() => { refresh(); }, []);

  async function saveQuota(e: React.FormEvent) {
    e.preventDefault(); setMessage(""); setError("");
    try {
      await createHajjQuota({ name_ar: quotaForm.name_ar, season: quotaForm.season, supplier_id: Number(quotaForm.supplier_id), total_units: Number(quotaForm.total_units), unit_cost: Number(quotaForm.unit_cost || 0) });
      setMessage("تم إنشاء حصة الحج وربطها بالمورد."); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "تعذر حفظ حصة الحج"); }
  }

  async function saveBooking(e: React.FormEvent) {
    e.preventDefault(); setMessage(""); setError("");
    try {
      const payload: any = {
        program_id: Number(bookingForm.program_id), pilgrim_id: Number(bookingForm.pilgrim_id), quota_id: Number(bookingForm.quota_id), sale_price: Number(bookingForm.sale_price),
        supplier_cost: bookingForm.supplier_cost ? Number(bookingForm.supplier_cost) : undefined,
      };
      if (bookingForm.party_mode === "agent") payload.agent_id = Number(bookingForm.agent_id); else payload.customer_id = Number(bookingForm.customer_id);
      await createHajjBooking(payload); setMessage("تم تسجيل الحاج وربطه بالخدمة والوكيل/العميل وحصة المورد.");
      setBookingForm(v => ({ ...v, pilgrim_id: "", agent_id: "", customer_id: "", sale_price: "", supplier_cost: "" })); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "تعذر تسجيل الحاج"); }
  }

  async function post(id: number) {
    setMessage(""); setError("");
    try { await postHajjBooking(id); setMessage(`تم ترحيل حجز الحج #${id} وإنشاء القيد المحاسبي.`); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : "تعذر ترحيل الحجز"); }
  }

  return <main className="page">
    <div className="welcome"><div><span className="eyebrow">قسم الحج</span><h2>إدارة حصة الحج والحجاج والوكلاء</h2><p>كل حاج مرتبط بحصة ومورد وطرف مالي، مع سعر بيع وتكلفة وقيد محاسبي.</p></div></div>
    {(error || message) && <div className={error ? "error-banner" : "notice-banner"}>{error || message}</div>}
    <div className="stats compact">
      <div className="stat"><span>إجمالي الحصة</span><strong>{quotas.reduce((n,q)=>n+q.total_units,0)}</strong><small>حاج</small></div>
      <div className="stat"><span>المستخدم</span><strong>{quotas.reduce((n,q)=>n+q.used_units,0)}</strong><small>حاج</small></div>
      <div className="stat"><span>المتبقي</span><strong>{quotas.reduce((n,q)=>n+q.remaining_units,0)}</strong><small>حاج</small></div>
      <div className="stat"><span>حجوزات المسودة</span><strong>{bookings.filter(b=>b.status==="reserved").length}</strong><small>حجز</small></div>
    </div>

    <section className="panel">
      <div className="panel-head"><div><h3>حصة الحج</h3><p>مثال: وزارة الحج والعمرة — 118 حاجًا — تكلفة الحاج حسب المورد.</p></div></div>
      <form className="form-grid" onSubmit={saveQuota}>
        <label><span>اسم الحصة</span><input value={quotaForm.name_ar} onChange={e=>setQuotaForm({...quotaForm,name_ar:e.target.value})} required /></label>
        <label><span>الموسم</span><input value={quotaForm.season} onChange={e=>setQuotaForm({...quotaForm,season:e.target.value})} required placeholder="1448هـ" /></label>
        <label><span>المورد</span><select value={quotaForm.supplier_id} onChange={e=>setQuotaForm({...quotaForm,supplier_id:e.target.value})} required><option value="">اختر المورد...</option>{suppliers.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
        <label><span>عدد الحجاج</span><input type="number" min="1" value={quotaForm.total_units} onChange={e=>setQuotaForm({...quotaForm,total_units:e.target.value})} required /></label>
        <label><span>تكلفة الحاج من المورد</span><input type="number" min="0" value={quotaForm.unit_cost} onChange={e=>setQuotaForm({...quotaForm,unit_cost:e.target.value})} required /></label>
        <div className="form-actions"><button className="primary">حفظ الحصة</button></div>
      </form>
    </section>

    <section className="panel">
      <div className="panel-head"><div><h3>تسجيل حاج</h3><p>الوكيل هو الطرف المالي عند اختيار التسجيل بواسطة وكيل.</p></div></div>
      <form className="form-grid" onSubmit={saveBooking}>
        <label><span>برنامج الحج</span><select value={bookingForm.program_id} onChange={e=>setBookingForm({...bookingForm,program_id:e.target.value})} required><option value="">اختر البرنامج...</option>{hajjPrograms.map(p=><option key={p.id} value={p.id}>{p.code} - {p.name_ar}</option>)}</select></label>
        <label><span>الحاج</span><select value={bookingForm.pilgrim_id} onChange={e=>setBookingForm({...bookingForm,pilgrim_id:e.target.value})} required><option value="">اختر الحاج...</option>{pilgrims.map(p=><option key={p.id} value={p.id}>{p.full_name} — {p.passport_number || "بدون جواز"}</option>)}</select></label>
        <label><span>حصة الحج / المورد</span><select value={bookingForm.quota_id} onChange={e=>setBookingForm({...bookingForm,quota_id:e.target.value,supplier_cost:e.target.value?String(quotas.find(q=>q.id===Number(e.target.value))?.unit_cost??""):""})} required><option value="">اختر الحصة...</option>{quotas.filter(q=>q.remaining_units>0).map(q=><option key={q.id} value={q.id}>{q.name_ar} — المتبقي {q.remaining_units}</option>)}</select></label>
        <label><span>نوع الطرف</span><select value={bookingForm.party_mode} onChange={e=>setBookingForm({...bookingForm,party_mode:e.target.value,agent_id:"",customer_id:""})}><option value="agent">وكيل</option><option value="customer">عميل مباشر</option></select></label>
        {bookingForm.party_mode === "agent" ? <label><span>الوكيل</span><select value={bookingForm.agent_id} onChange={e=>setBookingForm({...bookingForm,agent_id:e.target.value})} required><option value="">اختر الوكيل...</option>{agents.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</select></label> : <label><span>العميل</span><select value={bookingForm.customer_id} onChange={e=>setBookingForm({...bookingForm,customer_id:e.target.value})} required><option value="">اختر العميل...</option>{customers.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>}
        <label><span>سعر البيع على الطرف</span><input type="number" min="0.01" value={bookingForm.sale_price} onChange={e=>setBookingForm({...bookingForm,sale_price:e.target.value})} required /></label>
        <label><span>تكلفة المورد</span><input type="number" min="0" value={bookingForm.supplier_cost} onChange={e=>setBookingForm({...bookingForm,supplier_cost:e.target.value})} /></label>
        <div className="form-actions"><button className="primary">تسجيل الحاج</button>{selectedQuota&&<span className="muted">تكلفة الحصة الافتراضية: {money(selectedQuota.unit_cost)}</span>}</div>
      </form>
    </section>

    <section className="panel"><div className="panel-head"><div><h3>حصص الحج المسجلة</h3></div></div><div className="table-wrap"><table><thead><tr><th>الحصة</th><th>الموسم</th><th>المورد</th><th>الإجمالي</th><th>المستخدم</th><th>المتبقي</th><th>التكلفة</th></tr></thead><tbody>{quotas.map(q=><tr key={q.id}><td>{q.name_ar}</td><td>{q.season}</td><td>{suppliers.find(s=>s.id===q.supplier_id)?.name||q.supplier_id}</td><td>{q.total_units}</td><td>{q.used_units}</td><td>{q.remaining_units}</td><td>{money(q.unit_cost)}</td></tr>)}</tbody></table></div></section>

    <section className="panel"><div className="panel-head"><div><h3>سجل حجاج الحج</h3><p>عند الترحيل ينشأ قيد: الطرف مدين، إيراد الحج دائن، والتكلفة على المورد.</p></div></div><div className="table-wrap"><table><thead><tr><th>#</th><th>الحاج</th><th>الوكيل/العميل</th><th>البيع</th><th>التكلفة</th><th>المتبقي</th><th>الحالة</th><th>الإجراء</th></tr></thead><tbody>{bookings.map(b=><tr key={b.id}><td>{b.id}</td><td>{pilgrims.find(p=>p.id===b.pilgrim_id)?.full_name||b.pilgrim_id}</td><td>{b.agent_id?agents.find(a=>a.id===b.agent_id)?.name||`وكيل #${b.agent_id}`:customers.find(c=>c.id===b.customer_id)?.name||`عميل #${b.customer_id}`}</td><td>{money(b.sale_price)}</td><td>{money(b.supplier_cost)}</td><td>{money(b.remaining_amount)}</td><td>{b.status==='reserved'?'مسودة/محجوز':b.status==='confirmed'?'مرحّل':'ملغى'}</td><td>{b.status==='reserved'&&<button className="link" onClick={()=>post(b.id)}>ترحيل</button>}</td></tr>)}</tbody></table></div></section>
  </main>;
}
