import React,{useState} from "react";
type ModuleId="hajj"|"umrah"|"flight"|"buses"|"extra_visit"|"extra_work_visa"|"accounts"|"vouchers"|"journals"|"expenses"|"ar_ap"|"accounting_controls"|"settings";
type Node={id:string;label:string;target?:string;children?:Node[]};
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
 {id:"accounts",label:"الدليل المحاسبي",children:[
  {id:"a1",label:"تهيئة الأستاذ العام",children:[{id:"a11",label:"دليل الحسابات",target:"دليل الحسابات"}]},
  {id:"a2",label:"المدخلات",children:[
   {id:"a21",label:"الموردون",target:"الموردون"},
   {id:"a22",label:"الصناديق والبنوك والمحافظ",target:"الصناديق والبنوك والمحافظ"}
  ]},
  {id:"a3",label:"العمليات",children:[
   {id:"a31",label:"كشف حساب طرف",target:"كشف حساب طرف"},
   {id:"a32",label:"سداد مستحقات الموردين",target:"سداد مستحقات الموردين"}
  ]},
  {id:"a4",label:"التقارير",children:[
   {id:"a41",label:"الملخص المالي",target:"الملخص المالي"},
   {id:"a42",label:"اليومية",target:"اليومية"},
   {id:"a43",label:"ميزان المراجعة",target:"ميزان المراجعة"},
   {id:"a44",label:"الأرباح والخسائر",target:"الأرباح والخسائر"},
   {id:"a45",label:"الأستاذ العام",target:"الأستاذ العام"}
  ]}
 ]},
 {id:"vouchers",label:"السندات",children:[{id:"v1",label:"سند قبض",target:"سند قبض"},{id:"v2",label:"سند صرف",target:"سند صرف"}]},
 {id:"journals",label:"القيود اليومية",children:[
  {id:"j1",label:"قيد يومي جديد",target:"قيد يومي جديد"},
  {id:"j2",label:"القيود المسجلة",target:"القيود المسجلة"}
 ]},
 {id:"expenses",label:"المصروفات",children:[{id:"e1",label:"إدارة المصروفات",target:"إدارة المصروفات"}]},
 {id:"ar_ap",label:"الذمم",children:[
  {id:"r1",label:"الفواتير",target:"الفواتير"},
  {id:"r2",label:"تخصيص الدفعات",target:"المدفوعات"},
  {id:"r3",label:"أعمار الذمم",target:"أعمار الذمم"}
 ]},
 {id:"accounting_controls",label:"الضبط المحاسبي",children:[{id:"c1",label:"الأبعاد والفترات وسجل التدقيق",target:"الضبط المحاسبي"}]},
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
const ROOTS=new Set<ModuleId>(["hajj","umrah","flight","buses","extra_visit","extra_work_visa","accounts","vouchers","journals","expenses","ar_ap","accounting_controls","settings"]);
function TreeNode({node,activeModule,onNavigate,level=0}:{node:Node;activeModule:ModuleId;onNavigate:(m:ModuleId,t?:string)=>void;level?:number}){
 const [open,setOpen]=useState(level===0&&node.id===activeModule);
 const has=!!node.children?.length;
 const module=node.id===activeModule;
 return <div className="tree-node">
  <button className={`tree-row ${module?"active":""}`} style={{paddingInlineStart:10+level*18}} onClick={()=>{
   if(node.target){onNavigate(activeModule,node.target);return;}
   if(ROOTS.has(node.id as ModuleId)){onNavigate(node.id as ModuleId);setOpen(true);return;}
   if(has)setOpen(v=>!v);
  }}><span className="tree-caret">{has?(open?"⌄":"‹"):"•"}</span><span>{node.label}</span></button>
  {open&&node.children?.map(c=><TreeNode key={c.id} node={c} activeModule={activeModule} onNavigate={onNavigate} level={level+1}/>)}
 </div>
}
export default function SystemTree({activeModule,onNavigate}:{activeModule:ModuleId;onNavigate:(m:ModuleId,t?:string)=>void}){
 return <aside className="system-tree panel"><div className="tree-head"><span className="eyebrow">التنقل</span><h3>شجرة النظام</h3><p>كل شاشة وظيفية تظهر هنا، بدون تكرار داخل الصفحات.</p></div><div className="tree-body">{TREE.map(n=><TreeNode key={n.id} node={n} activeModule={activeModule} onNavigate={onNavigate}/>)}</div></aside>
}