import React,{useEffect,useMemo,useState} from "react";
import {createVoucher,getFinancial,getHajjBookings,getParties,getServices,getUmrahBookings,getVouchers,postVoucher,printVoucher,type Booking,type ServiceOrder} from "./api";

type ServiceType="hajj"|"umrah"|"flight"|"bus"|"visit"|"work_visa";
const TYPES:[ServiceType,string][]=[["hajj","الحج"],["umrah","العمرة"],["flight","الطيران"],["bus","الباصات"],["visit","الزيارات"],["work_visa","فيز العمل"]];
const money=(v:string|number)=>Number(v||0).toLocaleString("ar-YE",{minimumFractionDigits:2,maximumFractionDigits:2});
type Row=Booking|ServiceOrder;
const isBooking=(r:Row):r is Booking=>"program_id" in r;
const posted=(s:string)=>s==="posted"||s==="confirmed";

export default function ReceiptVoucherPage(){
 const [type,setType]=useState<ServiceType>("hajj");
 const [rows,setRows]=useState<Row[]>([]);
 const [agents,setAgents]=useState<any[]>([]);
 const [customers,setCustomers]=useState<any[]>([]);
 const [financial,setFinancial]=useState<any[]>([]);
 const [vouchers,setVouchers]=useState<any[]>([]);
 const [form,setForm]=useState({service_id:"",financial_id:"",manual_voucher_number:"",amount:"",date:new Date().toISOString().slice(0,10),description:""});
 const [error,setError]=useState("");
 const [message,setMessage]=useState("");
 const [busy,setBusy]=useState(false);

 async function refresh(){
   try{
     const [a,c,f,v]=await Promise.all([getParties("agent"),getParties("customer"),getFinancial(),getVouchers()]);
     setAgents(a);setCustomers(c);setFinancial(f);setVouchers(v);
     const data=type==="hajj"?await getHajjBookings():type==="umrah"?await getUmrahBookings():await getServices(type==="work_visa"?"work_visa":type);
     setRows(data);
     setError("");
   }catch(e){setError(e instanceof Error?e.message:"تعذر تحميل بيانات سندات القبض")}
 }
 useEffect(()=>{setForm(v=>({...v,service_id:"",amount:"",description:`تحصيل من خدمة `+ (TYPES.find(x=>x[0]===type)?.[1]||"") }));void refresh()},[type]);

 const collectable=useMemo(()=>rows.filter(r=>posted(r.status)&&Number(r.remaining_amount)>0),[rows]);
 const selected=collectable.find(r=>r.id===Number(form.service_id));
 function partyFor(r:Row){const id=r.agent_id||r.customer_id;return [...agents,...customers].find(x=>x.id===id)}
 const party=selected?partyFor(selected):null;
 const linkedType=type==="hajj"?"hajj_booking":type==="umrah"?"umrah_booking":"service_order";
 const label=TYPES.find(x=>x[0]===type)?.[1]||"الخدمة";

 async function save(e:React.FormEvent){
   e.preventDefault();setBusy(true);setError("");setMessage("");
   try{
     if(!selected)throw new Error(`اختر خدمة `+label);
     if(!party?.account_id)throw new Error("الطرف المرتبط بالخدمة غير مربوط بحساب محاسبي");
     const fa=financial.find(x=>x.id===Number(form.financial_id));
     if(!fa?.ledger_account_id)throw new Error("اختر صندوقًا أو بنكًا أو محفظة مرتبطة بحساب محاسبي");
     const amount=Number(form.amount);
     if(amount<=0)throw new Error("أدخل مبلغ تحصيل صحيح");
     if(amount>Number(selected.remaining_amount))throw new Error("مبلغ التحصيل أكبر من المتبقي على الخدمة");
     const v=await createVoucher({manual_voucher_number:form.manual_voucher_number.trim()||undefined,voucher_type:"receipt",voucher_date:form.date,amount,description:form.description,source_account_id:Number(party.account_id),destination_account_id:Number(fa.ledger_account_id),linked_service_type:linkedType,linked_service_id:selected.id});
     await postVoucher(v.id);
     setMessage(`تم ترحيل سند القبض `+v.voucher_number+` وربطه بخدمة `+(TYPES.find(x=>x[0]===type)?.[1]||"")+` #`+selected.id+`.`);
     setForm(v=>({...v,manual_voucher_number:"",amount:"",service_id:""}));
     await refresh();
   }catch(e){setError(e instanceof Error?e.message:"تعذر تسجيل سند القبض")}finally{setBusy(false)}
 }
 return <main className="page">
   <div className="welcome"><div><span className="eyebrow">المعاملات المالية</span><h2>سندات القبض</h2><p>شاشة موحدة لجميع الخدمات. حدّد نوع الخدمة أولًا، ثم اختر الخدمة وحساب الاستلام ليتم إنشاء السند وترحيله وربطه بالخدمة.</p></div></div>
   {(error||message)&&<div className={error?"error-banner":"notice-banner"}>{error||message}</div>}
   <section className="panel">
    <div className="panel-head"><div><h3>سند قبض جديد</h3><p>لا توجد شاشة قبض مستقلة لكل خدمة؛ نوع الخدمة يحدد السجلات المتاحة وربط السند بها.</p></div></div>
    <div className="form-grid">
      <label><span>نوع الخدمة</span><select value={type} onChange={e=>setType(e.target.value as ServiceType)}>{TYPES.map(([k,l])=><option key={k} value={k}>{l}</option>)}</select></label>
      <label><span>الخدمة المستحقة</span><select value={form.service_id} onChange={e=>setForm({...form,service_id:e.target.value})} required><option value="">اختر خدمة {label}...</option>{collectable.map(r=><option key={r.id} value={r.id}>#{r.id} — المتبقي {money(r.remaining_amount)} — {isBooking(r)?`حجز `+r.id:r.reference_no}</option>)}</select></label>
      <label><span>الطرف</span><input value={party?.name||""} readOnly placeholder="يظهر تلقائيًا من الخدمة"/></label>
      <label><span>حساب الطرف</span><input value={party?.account_id?String(party.account_id):""} readOnly placeholder="يظهر تلقائيًا"/></label>
      <label><span>حساب الاستلام</span><select value={form.financial_id} onChange={e=>setForm({...form,financial_id:e.target.value})} required><option value="">اختر صندوق/بنك/محفظة...</option>{financial.filter(f=>f.is_active!==false).map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select></label>
      <label><span>المبلغ</span><input type="number" min="0.01" step="0.01" value={form.amount} onChange={e=>setForm({...form,amount:e.target.value})} required/></label>
      <label><span>التاريخ</span><input type="date" value={form.date} onChange={e=>setForm({...form,date:e.target.value})} required/></label>
      <label><span>رقم السند اليدوي (اختياري)</span><input value={form.manual_voucher_number} onChange={e=>setForm({...form,manual_voucher_number:e.target.value})} placeholder="اتركه للترقيم التلقائي"/></label>
      <label className="full"><span>البيان</span><input value={form.description} onChange={e=>setForm({...form,description:e.target.value})} required/></label>
      <div className="form-actions"><button className="primary" disabled={busy}>{busy?"جارٍ الترحيل…":"حفظ وترحيل سند القبض"}</button></div>
    </div>
   </section>
   <section className="panel" style={{marginTop:20}}>
    <div className="panel-head"><div><h3>آخر سندات القبض</h3><p>السندات المرحّلة من جميع الخدمات في سجل واحد.</p></div></div>
    <div className="table-wrap"><table><thead><tr><th>رقم السند</th><th>التاريخ</th><th>الخدمة</th><th>المبلغ</th><th>البيان</th><th>الحالة</th><th>طباعة</th></tr></thead><tbody>
      {vouchers.filter(v=>v.voucher_type==="receipt").slice(0,30).map(v=><tr key={v.id}><td>{v.voucher_number}</td><td>{v.voucher_date}</td><td>{v.linked_service_type||"—"} #{v.linked_service_id||""}</td><td>{money(v.amount)}</td><td>{v.description}</td><td>{v.status}</td><td><button className="link" onClick={()=>void printVoucher(v.id)}>🖨️ طباعة</button></td></tr>)}
      {!vouchers.some(v=>v.voucher_type==="receipt")&&<tr><td colSpan={7}>لا توجد سندات قبض حتى الآن.</td></tr>}
    </tbody></table></div>
   </section>
 </main>;
}
