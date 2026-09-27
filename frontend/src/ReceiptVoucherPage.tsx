import React,{useEffect,useMemo,useState} from "react";
import {createParty,createVoucher,getFinancial,getHajjBookings,getParties,getServices,getUmrahBookings,getVouchers,postVoucher,printVoucher,type Booking,type ServiceOrder} from "./api";

type ServiceType="hajj"|"umrah"|"flight"|"bus"|"visit"|"work_visa";
type Row=Booking|ServiceOrder;
const TYPES:[ServiceType,string][]=[["hajj","الحج"],["umrah","العمرة"],["flight","الطيران"],["bus","الباصات"],["visit","الزيارات"],["work_visa","فيز العمل"]];
const PARTY_TYPES:[string,string][]=[["customer","عميل"],["agent","وكيل"]];
const money=(v:any)=>Number(v||0).toLocaleString("ar-YE",{minimumFractionDigits:2,maximumFractionDigits:2});
const isBooking=(r:Row):r is Booking=>"program_id" in r;

export default function ReceiptVoucherPage(){
 const [type,setType]=useState<ServiceType>("hajj"),[rows,setRows]=useState<Row[]>([]);
 const [parties,setParties]=useState<any[]>([]),[financial,setFinancial]=useState<any[]>([]),[vouchers,setVouchers]=useState<any[]>([]);
 const [form,setForm]=useState({service_id:"",party_id:"",financial_id:"",manual_voucher_number:"",amount:"",date:new Date().toISOString().slice(0,10),description:""});
 const [newParty,setNewParty]=useState({name:"",party_type:"customer",phone:""}),[showNewParty,setShowNewParty]=useState(false);
 const [error,setError]=useState(""),[message,setMessage]=useState(""),[busy,setBusy]=useState(false),[partyBusy,setPartyBusy]=useState(false);
 async function refresh(){
   try{
     const [customer,agent,f,v]=await Promise.all([getParties("customer"),getParties("agent"),getFinancial(),getVouchers()]);
     setParties([...customer,...agent]);setFinancial(f);setVouchers(v);
     const data=type==="hajj"?await getHajjBookings():type==="umrah"?await getUmrahBookings():await getServices(type);
     setRows(data);setError("");
   }catch(e){setError(e instanceof Error?e.message:"تعذر تحميل بيانات سندات القبض")}
 }
 useEffect(()=>{setForm(v=>({...v,service_id:"",amount:"",party_id:"",description:"تحصيل من خدمة "+(TYPES.find(x=>x[0]===type)?.[1]||"")}));void refresh()},[type]);
 const collectable=useMemo(()=>rows.filter(r=>!!(r as any).journal_entry_id&&Number(r.remaining_amount)>0&&r.status!=="cancelled"),[rows]);
 const selected=collectable.find(r=>r.id===Number(form.service_id));
 const partyFor=(r:Row)=>{const id=(r as any).agent_id||(r as any).customer_id;return parties.find(x=>x.id===id)||null};
 const selectedParty=selected?partyFor(selected):parties.find(x=>x.id===Number(form.party_id))||null;
 const linkedType=type==="hajj"?"hajj_booking":type==="umrah"?"umrah_booking":"service_order";
 const label=TYPES.find(x=>x[0]===type)?.[1]||"الخدمة";
 async function addParty(){
   setPartyBusy(true);setError("");setMessage("");
   try{
     if(!newParty.name.trim())throw new Error("اسم المستفيد مطلوب");
     const p=await createParty({name:newParty.name.trim(),party_type:newParty.party_type,phone:newParty.phone.trim()||undefined});
     setParties(prev=>[p,...prev]);setForm(v=>({...v,party_id:String(p.id)}));setNewParty({name:"",party_type:"customer",phone:""});setShowNewParty(false);
     setMessage("تمت إضافة المستفيد وربطه تلقائيًا بحسابه المحاسبي.");
   }catch(e){setError(e instanceof Error?e.message:"تعذر إضافة المستفيد")}finally{setPartyBusy(false)}
 }
 async function save(e:React.FormEvent){
   e.preventDefault();setBusy(true);setError("");setMessage("");
   try{
     if(!selectedParty)throw new Error("حدد اسم المستفيد");
     if(!selectedParty.account_id)throw new Error("المستفيد موجود لكنه غير مربوط بحساب محاسبي");
     if(selected){const serviceParty=partyFor(selected);if(!serviceParty||serviceParty.id!==selectedParty.id)throw new Error("المستفيد يجب أن يطابق الطرف المالي للخدمة المرتبطة")}
     const fa=financial.find(x=>x.id===Number(form.financial_id));
     if(!fa?.ledger_account_id)throw new Error("اختر صندوقًا أو بنكًا أو محفظة مرتبطة بحساب محاسبي");
     const amount=Number(form.amount);
     if(amount<=0)throw new Error("أدخل مبلغ تحصيل صحيح");
     if(selected&&amount>Number(selected.remaining_amount))throw new Error("مبلغ التحصيل أكبر من المتبقي على الخدمة");
     const v=await createVoucher({manual_voucher_number:form.manual_voucher_number.trim()||undefined,voucher_type:"receipt",voucher_date:form.date,beneficiary_name:selectedParty.name,amount,description:form.description,source_account_id:Number(selectedParty.account_id),destination_account_id:Number(fa.ledger_account_id),linked_service_type:selected?linkedType:undefined,linked_service_id:selected?.id});
     await postVoucher(v.id);
     setMessage("تم ترحيل سند القبض "+v.voucher_number+" باسم المستفيد: "+selectedParty.name+".");
     setForm(v=>({...v,manual_voucher_number:"",amount:"",service_id:"",party_id:""}));await refresh();
   }catch(e){setError(e instanceof Error?e.message:"تعذر تسجيل سند القبض")}finally{setBusy(false)}
 }
 return <main className="page">
   <div className="welcome"><div><span className="eyebrow">المعاملات المالية</span><h2>سندات القبض</h2><p>شاشة موحدة للنظام كله. يمكن ربط القبض بخدمة أو تسجيل قبض عام باسم عميل أو وكيل.</p></div></div>
   {(error||message)&&<div className={error?"error-banner":"notice-banner"}>{error||message}</div>}
   <section className="panel"><div className="panel-head"><div><h3>سند قبض جديد</h3><p>اسم المستفيد إلزامي؛ إن لم يكن موجودًا أضفه كعميل أو وكيل وسيُنشأ حسابه المحاسبي تلقائيًا.</p></div></div>
    <div className="form-grid">
      <label><span>اسم المستفيد</span><select value={selectedParty?.id?String(selectedParty.id):""} disabled={!!selected} onChange={e=>setForm({...form,party_id:e.target.value})} required><option value="">اختر العميل أو الوكيل...</option>{parties.map(p=><option key={p.id} value={p.id}>{p.name} — {p.party_type==="agent"?"وكيل":"عميل"}</option>)}</select></label>
      <label><span>نوع الخدمة</span><select value={type} onChange={e=>setType(e.target.value as ServiceType)}>{TYPES.map(([k,l])=><option key={k} value={k}>{l}</option>)}</select></label>
      <label><span>الخدمة المرتبطة (اختياري)</span><select value={form.service_id} onChange={e=>{const id=e.target.value;const row=collectable.find(x=>x.id===Number(id));const p=row?partyFor(row):null;setForm({...form,service_id:id,party_id:p?String(p.id):form.party_id})}}><option value="">قبض عام بدون ربط بخدمة</option>{collectable.map(r=><option key={r.id} value={r.id}>#{r.id} — المتبقي {money(r.remaining_amount)} — {isBooking(r)?"حجز":"خدمة "+r.reference_no}</option>)}</select></label>
      <label><span>الحساب المحاسبي للمستفيد</span><input value={selectedParty?.account_id?String(selectedParty.account_id):""} readOnly placeholder="يُنشأ/يظهر تلقائيًا"/></label>
      <label><span>حساب الاستلام</span><select value={form.financial_id} onChange={e=>setForm({...form,financial_id:e.target.value})} required><option value="">اختر صندوق/بنك/محفظة...</option>{financial.filter(f=>f.is_active!==false).map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select></label>
      <label><span>المبلغ</span><input type="number" min="0.01" step="0.01" value={form.amount} onChange={e=>setForm({...form,amount:e.target.value})} required/></label>
      <label><span>التاريخ</span><input type="date" value={form.date} onChange={e=>setForm({...form,date:e.target.value})} required/></label>
      <label><span>رقم السند اليدوي (اختياري)</span><input value={form.manual_voucher_number} onChange={e=>setForm({...form,manual_voucher_number:e.target.value})}/></label>
      <label className="full"><span>البيان</span><input value={form.description} onChange={e=>setForm({...form,description:e.target.value})} required/></label>
      <div className="form-actions"><button type="button" className="link" onClick={()=>setShowNewParty(v=>!v)}>{showNewParty?"إخفاء إضافة المستفيد":"المستفيد غير موجود؟ إضافة عميل/وكيل"}</button><button className="primary" disabled={busy}>{busy?"جارٍ الترحيل…":"حفظ وترحيل سند القبض"}</button></div>
    </div>
    {showNewParty&&<div className="panel" style={{marginTop:18}}><div className="panel-head"><div><h3>إضافة مستفيد جديد</h3><p>سيتم إنشاء حساب ذمم مدينة تحت الأصول وربطه بالمستفيد.</p></div></div><div className="form-grid"><label><span>اسم المستفيد</span><input value={newParty.name} onChange={e=>setNewParty({...newParty,name:e.target.value})} required/></label><label><span>نوع المستفيد</span><select value={newParty.party_type} onChange={e=>setNewParty({...newParty,party_type:e.target.value})}>{PARTY_TYPES.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label><label><span>الهاتف</span><input value={newParty.phone} onChange={e=>setNewParty({...newParty,phone:e.target.value})}/></label><div className="form-actions"><button type="button" className="primary" disabled={partyBusy} onClick={()=>void addParty()}>{partyBusy?"جارٍ الإنشاء…":"إضافة المستفيد"}</button></div></div></div>}
   </section>
   <section className="panel" style={{marginTop:20}}><div className="panel-head"><div><h3>آخر سندات القبض</h3><p>سجل موحد للقبض العام والقبض المرتبط بالخدمات.</p></div></div><div className="table-wrap"><table><thead><tr><th>رقم السند</th><th>التاريخ</th><th>المستفيد</th><th>الخدمة</th><th>المبلغ</th><th>الحالة</th><th>طباعة</th></tr></thead><tbody>{vouchers.filter(v=>v.voucher_type==="receipt").slice(0,30).map(v=><tr key={v.id}><td>{v.voucher_number}</td><td>{v.voucher_date}</td><td>{v.beneficiary_name||"—"}</td><td>{v.linked_service_type? v.linked_service_type+" #"+(v.linked_service_id||"") :"قبض عام"}</td><td>{money(v.amount)}</td><td>{v.status}</td><td><button className="link" onClick={()=>void printVoucher(v.id)}>🖨️ طباعة</button></td></tr>)}{!vouchers.some(v=>v.voucher_type==="receipt")&&<tr><td colSpan={7}>لا توجد سندات قبض حتى الآن.</td></tr>}</tbody></table></div></section>
 </main>;
}