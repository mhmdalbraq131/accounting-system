import React,{useEffect,useState} from "react";
import {closeFiscalPeriod,createAccountingDimension,createFiscalPeriod,getAccountingDimensions,getAuditLogs,getFiscalPeriods,type AccountingDimension,type AuditLog,type FiscalPeriod} from "./api";

export default function AccountingControlsPage(){
  const [dimensions,setDimensions]=useState<AccountingDimension[]>([]);
  const [periods,setPeriods]=useState<FiscalPeriod[]>([]);
  const [logs,setLogs]=useState<AuditLog[]>([]);
  const [code,setCode]=useState(""); const [name,setName]=useState("");
  const [periodName,setPeriodName]=useState(""); const [start,setStart]=useState(""); const [end,setEnd]=useState("");
  const [error,setError]=useState("");
  async function load(){setError(""); const results=await Promise.allSettled([getAccountingDimensions(),getFiscalPeriods(),getAuditLogs(100)]); const [d,p,l]=results; if(d.status==="fulfilled")setDimensions(d.value); if(p.status==="fulfilled")setPeriods(p.value); if(l.status==="fulfilled")setLogs(l.value); const failed=results.find(x=>x.status==="rejected") as PromiseRejectedResult|undefined; if(failed)setError(failed.reason instanceof Error?failed.reason.message:"تعذر تحميل بعض بيانات الضبط المحاسبي")}
  useEffect(()=>{load()},[]);
  async function addDimension(e:React.FormEvent){e.preventDefault();try{await createAccountingDimension({dimension_type:"cost_center",code,name_ar:name});setCode("");setName("");await load()}catch(e){setError(e instanceof Error?e.message:"تعذر إضافة البعد")}}
  async function addPeriod(e:React.FormEvent){e.preventDefault();try{await createFiscalPeriod({name:periodName,start_date:start,end_date:end});setPeriodName("");setStart("");setEnd("");await load()}catch(e){setError(e instanceof Error?e.message:"تعذر إضافة الفترة")}}
  async function close(id:number){try{await closeFiscalPeriod(id);await load()}catch(e){setError(e instanceof Error?e.message:"تعذر إغلاق الفترة")}}
  return <div className="page-stack" dir="rtl">
    <div className="panel"><div className="panel-head"><div><h2>الضبط المحاسبي</h2><p>أبعاد محاسبية وفترات مالية وسجل تدقيق، مستوحاة من ممارسات ERPNext.</p></div></div>{error&&<div className="error-banner">{error}</div>}
      <div className="grid-2">
        <form className="card" onSubmit={addDimension}><h3>مركز تكلفة / بُعد محاسبي</h3><label>الرمز<input value={code} onChange={e=>setCode(e.target.value)} required/></label><label>الاسم<input value={name} onChange={e=>setName(e.target.value)} required/></label><button className="primary">إضافة البعد</button></form>
        <form className="card" onSubmit={addPeriod}><h3>فترة محاسبية</h3><label>الاسم<input value={periodName} onChange={e=>setPeriodName(e.target.value)} placeholder="2026" required/></label><label>من<input type="date" value={start} onChange={e=>setStart(e.target.value)} required/></label><label>إلى<input type="date" value={end} onChange={e=>setEnd(e.target.value)} required/></label><button className="primary">إضافة الفترة</button></form>
      </div>
    </div>
    <div className="panel"><div className="panel-head"><h3>الأبعاد المحاسبية</h3></div><div className="table-wrap"><table><thead><tr><th>الرمز</th><th>الاسم</th><th>النوع</th></tr></thead><tbody>{dimensions.map(d=><tr key={d.id}><td>{d.code}</td><td>{d.name_ar}</td><td>{d.dimension_type}</td></tr>)}</tbody></table></div></div>
    <div className="panel"><div className="panel-head"><h3>الفترات المحاسبية</h3></div><div className="table-wrap"><table><thead><tr><th>الفترة</th><th>من</th><th>إلى</th><th>الحالة</th><th></th></tr></thead><tbody>{periods.map(p=><tr key={p.id}><td>{p.name}</td><td>{p.start_date}</td><td>{p.end_date}</td><td>{p.is_closed?"مغلقة":"مفتوحة"}</td><td>{!p.is_closed&&<button className="secondary" onClick={()=>close(p.id)}>إغلاق الفترة</button>}</td></tr>)}</tbody></table></div></div>
    <div className="panel"><div className="panel-head"><h3>سجل التدقيق</h3></div><div className="table-wrap"><table><thead><tr><th>الوقت</th><th>العملية</th><th>النوع</th><th>المعرف</th></tr></thead><tbody>{logs.map(l=><tr key={l.id}><td>{new Date(l.created_at).toLocaleString("ar-YE")}</td><td>{l.action}</td><td>{l.entity_type}</td><td>{l.entity_id??"—"}</td></tr>)}</tbody></table></div></div>
  </div>
}
