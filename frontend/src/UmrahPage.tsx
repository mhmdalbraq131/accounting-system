import React, { useEffect, useMemo, useState } from "react";
import {
  createUmrahBooking,
  createVoucher,
  getFinancial,
  getUmrahBookings,
  getParties,
  postUmrahBooking,
  postVoucher,
  type Booking,
  type Pilgrim,
  type Program,
} from "./api";

const money=(v:string|number)=>Number(v||0).toLocaleString("ar-YE",{minimumFractionDigits:2,maximumFractionDigits:2});

export default function UmrahPage({programs,pilgrims,suppliers,customers}:{programs:Program[];pilgrims:Pilgrim[];suppliers:any[];customers:any[]}){
  const [bookings,setBookings]=useState<Booking[]>([]),[agents,setAgents]=useState<any[]>([]),[financial,setFinancial]=useState<any[]>([]);
  const [mode,setMode]=useState("agent"),[message,setMessage]=useState(""),[error,setError]=useState("");
  const [form,setForm]=useState({program_id:"",pilgrim_id:"",agent_id:"",customer_id:"",supplier_id:"",sale_price:"",supplier_cost:""});
  const [receipt,setReceipt]=useState({booking_id:"",financial_id:"",amount:"",date:new Date().toISOString().slice(0,10),description:"تحصيل من خدمة عمرة"});
  const umrahPrograms=useMemo(()=>programs.filter(p=>p.program_type==="umrah"&&p.is_active),[programs]);
  const selected=bookings.find(b=>b.id===Number(receipt.booking_id));
  async function refresh(){try{const [b,a,f]=await Promise.all([getUmrahBookings(),getParties("agent"),getFinancial()]);setBookings(b);setAgents(a);setFinancial(f);setError("")}catch(e){setError(e instanceof Error?e.message:"تعذر تحميل بيانات العمرة")}}
  useEffect(()=>{refresh()},[]);
  async function save(e:React.FormEvent){e.preventDefault();setMessage("");setError("");try{
    await createUmrahBooking({program_id:Number(form.program_id),pilgrim_id:Number(form.pilgrim_id),supplier_id:Number(form.supplier_id),sale_price:Number(form.sale_price),supplier_cost:Number(form.supplier_cost||0),...(mode==="agent"?{agent_id:Number(form.agent_id)}:{customer_id:Number(form.customer_id)})});
    setForm(v=>({...v,pilgrim_id:"",agent_id:"",customer_id:"",sale_price:"",supplier_cost:""}));setMessage("تم تسجيل خدمة العمرة.");await refresh();
  }catch(e){setError(e instanceof Error?e.message:"تعذر تسجيل خدمة العمرة")}}
  async function post(id:number){setMessage("");setError("");try{await postUmrahBooking(id);setMessage(`تم ترحيل خدمة العمرة #${id} وإنشاء القيد.`);await refresh()}catch(e){setError(e instanceof Error?e.message:"تعذر ترحيل الخدمة")}}
  async function collect(e:React.FormEvent){e.preventDefault();setMessage("");setError("");try{
    if(!selected)throw new Error("اختر خدمة عمرة");
    const partyId=selected.agent_id||selected.customer_id;const payer=[...agents,...customers].find(x=>x.id===partyId);if(!payer?.account_id)throw new Error("الطرف غير مربوط بحساب محاسبي");
    const f=financial.find(x=>x.id===Number(receipt.financial_id));if(!f?.ledger_account_id)throw new Error("حساب الاستلام غير صالح");
    const amount=Number(receipt.amount);if(!amount||amount<=0)throw new Error("أدخل مبلغًا صحيحًا");
    const v=await createVoucher({voucher_type:"receipt",voucher_date:receipt.date,amount,description:receipt.description,source_account_id:Number(payer.account_id),destination_account_id:Number(f.ledger_account_id),linked_service_type:"umrah_booking",linked_service_id:selected.id});
    await postVoucher(v.id);setReceipt(r=>({...r,amount:""}));setMessage(`تم تحصيل ${money(amount)} وربطه بخدمة العمرة #${selected.id}.`);await refresh();
  }catch(e){setError(e instanceof Error?e.message:"تعذر تسجيل التحصيل")}}
  return <main className="page">
    <div className="welcome"><div><span className="eyebrow">قسم العمرة</span><h2>البرامج والحجوزات والتحصيل المحاسبي</h2><p>الوكيل أو العميل طرف مالي، والمورد مستقل عن الطرف، مع سعر البيع والتكلفة والربح والقيد.</p></div></div>
    {(error||message)&&<div className={error?"error-banner":"notice-banner"}>{error||message}</div>}
    <div className="stats compact"><Stat label="الحجوزات" value={bookings.length} unit="خدمة"/><Stat label="المرحّلة" value={bookings.filter(b=>b.status==="confirmed").length} unit="خدمة"/><Stat label="إجمالي البيع" value={money(bookings.reduce((n,b)=>n+Number(b.sale_price),0))} unit="ريال"/><Stat label="إجمالي الربح" value={money(bookings.reduce((n,b)=>n+Number(b.profit),0))} unit="ريال"/></div>
    <section className="panel"><div className="panel-head"><div><h3>تسجيل خدمة عمرة</h3><p>اختر الطرف والمورد ثم حدّد سعر البيع وتكلفة المورد.</p></div></div>
      <form className="form-grid" onSubmit={save}>
        <Select label="برنامج العمرة" value={form.program_id} onChange={v=>setForm({...form,program_id:v})} options={umrahPrograms.map(p=>({value:String(p.id),label:`${p.code} - ${p.name_ar}`}))}/>
        <Select label="المعتمر" value={form.pilgrim_id} onChange={v=>setForm({...form,pilgrim_id:v})} options={pilgrims.map(p=>({value:String(p.id),label:p.full_name}))}/>
        <Select label="المورد" value={form.supplier_id} onChange={v=>setForm({...form,supplier_id:v})} options={suppliers.map(s=>({value:String(s.id),label:s.name}))}/>
        <label><span>نوع الطرف</span><select value={mode} onChange={e=>{setMode(e.target.value);setForm({...form,agent_id:"",customer_id:""})}}><option value="agent">وكيل</option><option value="customer">عميل مباشر</option></select></label>
        {mode==="agent"?<Select label="الوكيل" value={form.agent_id} onChange={v=>setForm({...form,agent_id:v})} options={agents.map(a=>({value:String(a.id),label:a.name}))}/>:<Select label="العميل" value={form.customer_id} onChange={v=>setForm({...form,customer_id:v})} options={customers.map(c=>({value:String(c.id),label:c.name}))}/>} 
        <NumberField label="سعر البيع" value={form.sale_price} onChange={v=>setForm({...form,sale_price:v})} required/>
        <NumberField label="تكلفة المورد" value={form.supplier_cost} onChange={v=>setForm({...form,supplier_cost:v})}/>
        <div className="form-actions"><button className="primary">تسجيل الخدمة</button></div>
      </form>
    </section>
    <section className="panel"><div className="panel-head"><div><h3>سند قبض مرتبط بخدمة العمرة</h3><p>لا يتم تحديث مدفوعات الخدمة إلا بعد ترحيل السند المرتبط بها.</p></div></div>
      <form className="form-grid" onSubmit={collect}>
        <Select label="الخدمة" value={receipt.booking_id} onChange={v=>setReceipt({...receipt,booking_id:v})} options={bookings.filter(b=>b.status==="confirmed"&&Number(b.remaining_amount)>0).map(b=>({value:String(b.id),label:`#${b.id} — المتبقي ${money(b.remaining_amount)}`}))}/>
        <Select label="حساب الاستلام" value={receipt.financial_id} onChange={v=>setReceipt({...receipt,financial_id:v})} options={financial.map(f=>({value:String(f.id),label:f.name}))}/>
        <NumberField label="المبلغ" value={receipt.amount} onChange={v=>setReceipt({...receipt,amount:v})} required/>
        <label><span>التاريخ</span><input type="date" value={receipt.date} onChange={e=>setReceipt({...receipt,date:e.target.value})} required/></label>
        <label><span>البيان</span><input value={receipt.description} onChange={e=>setReceipt({...receipt,description:e.target.value})} required/></label>
        <div className="form-actions"><button className="primary">حفظ وترحيل سند القبض</button></div>
      </form>
    </section>
    <section className="panel"><div className="panel-head"><div><h3>سجل خدمات العمرة</h3><p>المورد هو مصدر التكلفة، والوكيل/العميل هو صاحب الاستحقاق.</p></div></div><div className="table-wrap"><table><thead><tr><th>#</th><th>المعتمر</th><th>الطرف</th><th>البيع</th><th>التكلفة</th><th>الربح</th><th>المدفوع</th><th>المتبقي</th><th>الحالة</th><th>إجراء</th></tr></thead><tbody>{bookings.map(b=><tr key={b.id}><td>{b.id}</td><td>{pilgrims.find(p=>p.id===b.pilgrim_id)?.full_name||b.pilgrim_id}</td><td>{b.agent_id?agents.find(a=>a.id===b.agent_id)?.name||`وكيل #${b.agent_id}`:customers.find(c=>c.id===b.customer_id)?.name||`عميل #${b.customer_id}`}</td><td>{money(b.sale_price)}</td><td>{money(b.supplier_cost)}</td><td>{money(b.profit)}</td><td>{money(b.paid_amount)}</td><td>{money(b.remaining_amount)}</td><td>{b.status==="reserved"?"مسودة/محجوز":b.status==="confirmed"?"مرحّل":"ملغى"}</td><td>{b.status==="reserved"&&<button className="link" onClick={()=>post(b.id)}>ترحيل</button>}</td></tr>)}</tbody></table></div></section>
  </main>
}
function Select({label,value,onChange,options}:{label:string;value:string;onChange:(v:string)=>void;options:{value:string;label:string}[]}){return <label><span>{label}</span><select value={value} onChange={e=>onChange(e.target.value)} required><option value="">اختر...</option>{options.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}</select></label>}
function NumberField({label,value,onChange,required}:{label:string;value:string;onChange:(v:string)=>void;required?:boolean}){return <label><span>{label}</span><input type="number" min="0" step="0.01" value={value} onChange={e=>onChange(e.target.value)} required={required}/></label>}
function Stat({label,value,unit}:{label:string;value:string|number;unit:string}){return <div className="stat"><span>{label}</span><strong>{value}</strong><small>{unit}</small></div>}
