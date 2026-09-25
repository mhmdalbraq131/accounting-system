import React,{useEffect,useState} from "react";
import {createJournal,getAccounts,getJournals,postJournal,cancelJournal,getAccountingDimensions,type AccountingDimension} from "./api";

type Line={account_id:string;dimension_id:string;description:string;debit:string;credit:string};
const emptyLine=():Line=>({account_id:"",dimension_id:"",description:"",debit:"0",credit:"0"});
const money=(v:any)=>Number(v||0).toLocaleString("ar-YE",{minimumFractionDigits:2,maximumFractionDigits:2});

export default function JournalsPage(){
  const [accounts,setAccounts]=useState<any[]>([]);
  const [dimensions,setDimensions]=useState<AccountingDimension[]>([]);
  const [rows,setRows]=useState<any[]>([]);
  const [number,setNumber]=useState("");
  const [entryDate,setEntryDate]=useState(new Date().toISOString().slice(0,10));
  const [description,setDescription]=useState("");
  const [lines,setLines]=useState<Line[]>([emptyLine(),emptyLine()]);
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);

  async function load(){
    const [a,d,j]=await Promise.all([getAccounts(),getAccountingDimensions(),getJournals()]);
    setAccounts(a);setDimensions(d);setRows(j);
  }
  useEffect(()=>{void load().catch(e=>setError(e instanceof Error?e.message:"تعذر تحميل القيود"))},[]);

  const debit=lines.reduce((n,l)=>n+Number(l.debit||0),0);
  const credit=lines.reduce((n,l)=>n+Number(l.credit||0),0);
  const balanced=Math.abs(debit-credit)<0.005 && debit>0;

  function updateLine(i:number,key:keyof Line,value:string){
    setLines(prev=>prev.map((l,n)=>n===i?{...l,[key]:value}:l));
  }
  async function save(e:React.FormEvent){
    e.preventDefault();setBusy(true);setError("");
    try{
      await createJournal({
        entry_number:number,
        entry_date:entryDate,
        description,
        lines:lines.map(l=>({
          account_id:Number(l.account_id),
          dimension_id:l.dimension_id?Number(l.dimension_id):undefined,
          description:l.description||undefined,
          debit:Number(l.debit||0),
          credit:Number(l.credit||0)
        }))
      });
      setNumber("");setDescription("");setLines([emptyLine(),emptyLine()]);await load();
    }catch(e){setError(e instanceof Error?e.message:"تعذر حفظ القيد")}finally{setBusy(false)}
  }
  async function action(fn:(id:number)=>Promise<any>,id:number){
    setBusy(true);setError("");
    try{await fn(id);await load()}catch(e){setError(e instanceof Error?e.message:"تعذر تنفيذ العملية")}finally{setBusy(false)}
  }
  return <main className="page" dir="rtl">
    <div className="welcome"><div><span className="eyebrow">المحاسبة العامة</span><h2>القيود اليومية</h2><p>إنشاء القيد كمسودة ثم ترحيله. القيد المرحّل لا يُعدّل، ويُلغى بعكس محاسبي.</p></div></div>
    {error&&<div className="error-banner">{error}</div>}
    <section className="panel">
      <div className="panel-head"><div><h3>قيد يومي جديد</h3><p>يجب أن يتساوى إجمالي المدين والدائن.</p></div><strong>مدين: {money(debit)} • دائن: {money(credit)}</strong></div>
      <form onSubmit={save}>
        <div className="form-grid">
          <label><span>رقم القيد</span><input value={number} onChange={e=>setNumber(e.target.value)} required/></label>
          <label><span>التاريخ</span><input type="date" value={entryDate} onChange={e=>setEntryDate(e.target.value)} required/></label>
          <label style={{gridColumn:"1/-1"}}><span>البيان</span><input value={description} onChange={e=>setDescription(e.target.value)} required/></label>
        </div>
        <div className="table-wrap" style={{marginTop:18}}><table><thead><tr><th>الحساب</th><th>البعد</th><th>البيان</th><th>مدين</th><th>دائن</th><th></th></tr></thead><tbody>
          {lines.map((l,i)=><tr key={i}>
            <td><select value={l.account_id} onChange={e=>updateLine(i,"account_id",e.target.value)} required><option value="">اختر الحساب</option>{accounts.filter(a=>a.is_active).map(a=><option key={a.id} value={a.id}>{a.code} - {a.name_ar}</option>)}</select></td>
            <td><select value={l.dimension_id} onChange={e=>updateLine(i,"dimension_id",e.target.value)}><option value="">—</option>{dimensions.map(d=><option key={d.id} value={d.id}>{d.code} - {d.name_ar}</option>)}</select></td>
            <td><input value={l.description} onChange={e=>updateLine(i,"description",e.target.value)}/></td>
            <td><input type="number" min="0" step="0.01" value={l.debit} onChange={e=>updateLine(i,"debit",e.target.value)}/></td>
            <td><input type="number" min="0" step="0.01" value={l.credit} onChange={e=>updateLine(i,"credit",e.target.value)}/></td>
            <td><button type="button" className="link" onClick={()=>setLines(prev=>prev.length>2?prev.filter((_,n)=>n!==i):prev)}>حذف</button></td>
          </tr>)}
        </tbody></table></div>
        <div className="form-actions"><button type="button" className="secondary" onClick={()=>setLines(prev=>[...prev,emptyLine()])}>+ إضافة سطر</button><button className="primary" disabled={busy||!balanced}>{busy?"جارٍ الحفظ…":"حفظ كمسودة"}</button></div>
      </form>
    </section>
    <section className="panel"><div className="panel-head"><h3>القيود المسجلة ({rows.length})</h3></div><div className="table-wrap"><table><thead><tr><th>الرقم</th><th>التاريخ</th><th>البيان</th><th>الحالة</th><th>الإجمالي</th><th>إجراء</th></tr></thead><tbody>{rows.map(row=><tr key={row.id}><td>{row.entry_number}</td><td>{row.entry_date}</td><td>{row.description}</td><td>{row.status==="posted"?"مرحّل":row.status==="cancelled"?"ملغى":"مسودة"}</td><td>{money((row.lines||[]).reduce((n:any,l:any)=>n+Number(l.debit||0),0))}</td><td>{row.status==="draft"?<><button className="secondary" onClick={()=>void action(postJournal,row.id)}>ترحيل</button> <button className="link" onClick={()=>void action(cancelJournal,row.id)}>إلغاء</button></>:row.status==="posted"?<button className="link" onClick={()=>void action(cancelJournal,row.id)}>عكس القيد</button>:"—"}</td></tr>)}</tbody></table></div></section>
  </main>
}
