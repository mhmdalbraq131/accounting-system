import React,{useEffect,useState} from "react";
type ModuleId="hajj"|"umrah"|"flight"|"buses"|"extra_visit"|"extra_work_visa"|"accounts"|"vouchers"|"journals"|"expenses"|"ar_ap"|"accounting_controls"|"settings";
type Node={id:string;label:string;target?:string;module?:ModuleId;children?:Node[]};
const TREE:Node[]=[
 {id:"hajj",label:"الحج",children:[
  {id:"h0",label:"لوحة الحج",target:"لوحة الحج"},
  {id:"h1",label:"التهيئة",children:[{id:"h11",label:"البرامج",target:"برامج الحج"},{id:"h12",label:"الحصص والموردون",target:"الحصص والموردون"}]},
  {id:"h2",label:"المدخلات",children:[{id:"h21",label:"الحجاج",target:"الحجاج"},{id:"h22",label:"الوكلاء",target:"الوكلاء"}]},
  {id:"h3",label:"العمليات",children:[{id:"h31",label:"الحجوزات والخدمات",target:"الحجوزات والخدمات"}]},
  {id:"h4",label:"التقارير",children:[{id:"h41",label:"كشف حساب الأطراف",target:"كشف حساب طرف"}]}
 ]},
 {id:"umrah",label:"العمرة",children:[
  {id:"u1",label:"المدخلات",children:[{id:"u11",label:"تسجيل خدمة العمرة",target:"تسجيل خدمة عمرة"}]},
  {id:"u2",label:"العمليات",children:[{id:"u21",label:"سجل خدمات العمرة",target:"سجل خدمات العمرة"}]}
 ]},
 {id:"flight",label:"الطيران",children:[
  {id:"f1",label:"تسجيل الطيران",target:"تسجيل الطيران"},
  {id:"f2",label:"سجل الطيران",target:"سجل الطيران"}
 ]},
 {id:"buses",label:"الباصات",children:[
  {id:"b1",label:"تسجيل الباصات",target:"تسجيل الباصات"},
  {id:"b2",label:"سجل الباصات",target:"سجل الباصات"}
 ]},
 {id:"extra_visit",label:"الزيارات",children:[
  {id:"vst1",label:"تسجيل الزيارات",target:"تسجيل الزيارات"},
  {id:"vst2",label:"سجل الزيارات",target:"سجل الزيارات"}
 ]},
 {id:"extra_work_visa",label:"فيز العمل",children:[
  {id:"wv1",label:"تسجيل فيز العمل",target:"تسجيل فيز العمل"},
  {id:"wv2",label:"سجل فيز العمل",target:"سجل فيز العمل"}
 ]},
 {id:"accounts",label:"المحاسبة",children:[
  {id:"a1",label:"التهيئة المحاسبية",children:[
   {id:"a11",label:"دليل الحسابات",target:"دليل الحسابات",module:"accounts"},
   {id:"a12",label:"ربط الحسابات الافتراضية",target:"ربط الحسابات",module:"settings"},
   {id:"a13",label:"العملات",target:"العملات",module:"settings"},
   {id:"a14",label:"الأبعاد والفترات وسجل التدقيق",target:"الضبط المحاسبي",module:"accounting_controls"}
  ]},
  {id:"a2",label:"الحسابات المدينة",children:[
   {id:"a21",label:"فواتير العملاء",target:"الفواتير",module:"ar_ap"},
   {id:"a22",label:"أعمار الذمم المدينة",target:"أعمار الذمم",module:"ar_ap"},
   {id:"a23",label:"كشف حساب الطرف",target:"كشف حساب طرف",module:"accounts"}
  ]},
  {id:"a3",label:"الحسابات الدائنة",children:[
   {id:"a31",label:"الموردون",target:"الموردون",module:"accounts"},
   {id:"a32",label:"سداد مستحقات الموردين",target:"سداد مستحقات الموردين",module:"accounts"}
  ]},
  {id:"a4",label:"البنوك والصناديق",children:[
   {id:"a41",label:"الصناديق والبنوك والمحافظ",target:"الصناديق والبنوك والمحافظ",module:"accounts"},
   {id:"a42",label:"سند قبض",target:"سند قبض",module:"vouchers"},
   {id:"a43",label:"سند صرف",target:"سند صرف",module:"vouchers"},
   {id:"a44",label:"تخصيص الدفعات",target:"المدفوعات",module:"ar_ap"}
  ]},
  {id:"a5",label:"دفتر الأستاذ والقيود",children:[
   {id:"a51",label:"قيد يومي جديد",target:"قيد يومي جديد",module:"journals"},
   {id:"a52",label:"القيود المسجلة",target:"القيود المسجلة",module:"journals"},
   {id:"a53",label:"اليومية",target:"اليومية",module:"accounts"},
   {id:"a54",label:"الأستاذ العام",target:"الأستاذ العام",module:"accounts"}
  ]},
  {id:"a6",label:"المصروفات",children:[
   {id:"a61",label:"إدارة المصروفات",target:"إدارة المصروفات",module:"expenses"}
  ]},
  {id:"a7",label:"التقارير المالية",children:[
   {id:"a71",label:"الملخص المالي",target:"الملخص المالي",module:"accounts"},
   {id:"a72",label:"ميزان المراجعة",target:"ميزان المراجعة",module:"accounts"},
   {id:"a73",label:"الأرباح والخسائر",target:"الأرباح والخسائر",module:"accounts"}
  ]}
 ]},
 {id:"settings",label:"الإعدادات",children:[
  {id:"s1",label:"بيانات الوكالة",target:"الإعدادات العامة"},
  {id:"s2",label:"ربط الحسابات",target:"ربط الحسابات"},
  {id:"s3",label:"الفروع",target:"الفروع"},
  {id:"s4",label:"المستخدمون",target:"المستخدمون"},
  {id:"s5",label:"الأدوار والصلاحيات",target:"الأدوار والصلاحيات"},
  {id:"s6",label:"العملات",target:"العملات"},
  {id:"s7",label:"الخدمات الإضافية",target:"الخدمات الإضافية"}
 ]}
];
function TreeNode({node,activeModule,onNavigate,level=0}:{node:Node;activeModule:ModuleId;onNavigate:(m:ModuleId,t?:string)=>void;level?:number}){
 const has=!!node.children?.length;
 const [open,setOpen]=useState(level===0&&node.id===activeModule);
 const [selected,setSelected]=useState(false);
 useEffect(()=>{if(level===0&&node.id===activeModule)setOpen(true)},[activeModule,level,node.id]);
 const targetModule=node.module??activeModule;
 const navigate=()=>{if(node.target)onNavigate(targetModule,node.target)};
 const toggle=()=>{if(has)setOpen(v=>!v)};
 const onKeyDown=(e:React.KeyboardEvent<HTMLDivElement>)=>{
   if(e.key==="Enter"){e.preventDefault();if(node.target)navigate();else if(has)toggle();}
   else if(e.key==="ArrowRight"){if(has){e.preventDefault();setOpen(true)}}
   else if(e.key==="ArrowLeft"){if(has){e.preventDefault();setOpen(false)}}
 };
 return <div className="tree-node">
   <div className="tree-row-wrap" style={{paddingInlineStart:10+level*18}}>
     {has?<button type="button" className="tree-caret-btn" aria-label={(open?"طي ":"فتح ")+node.label} aria-expanded={open} onClick={toggle}>{open?"⌄":"‹"}</button>:<span className="tree-caret-spacer">•</span>}
     <div role="treeitem" tabIndex={0} aria-selected={selected} className={"tree-row "+(node.id===activeModule?"active ":"")+(selected?"selected":"")} onClick={()=>setSelected(true)} onDoubleClick={navigate} onKeyDown={onKeyDown}>
       <span>{node.label}</span>
     </div>
   </div>
   {open&&node.children?.map(c=><TreeNode key={c.id} node={c} activeModule={activeModule} onNavigate={onNavigate} level={level+1}/>)}
 </div>
}
export default function SystemTree({activeModule,onNavigate}:{activeModule:ModuleId;onNavigate:(m:ModuleId,t?:string)=>void}){
 return <aside className="system-tree panel"><div className="tree-head"><span className="eyebrow">التنقل</span><h3>شجرة النظام</h3><p>كل شاشة وظيفية تظهر هنا، بدون تكرار داخل الصفحات.</p></div><div className="tree-body">{TREE.map(n=><TreeNode key={n.id} node={n} activeModule={activeModule} onNavigate={onNavigate}/>)}</div></aside>
}