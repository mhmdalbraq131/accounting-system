import React,{useEffect,useState} from "react";
import {createRoot} from "react-dom/client";
import "./styles.css";
import {getParties,getPilgrims,getPrograms,login,type Pilgrim,type Program} from "./api";
import HajjPage from "./HajjPage";
import UmrahPage from "./UmrahPage";
import ServicePage from "./ServicePage";
import AccountsPage from "./AccountsPage";
import SettingsPage from "./SettingsPage";

const modules=[["hajj","الحج","🕋"],["umrah","العمرة","🌙"],["flight","الطيران","✈️"],["buses","الباصات","🚌"],["accounts","الدليل المحاسبي","≡"],["settings","الإعدادات","⚙"]] as const;

function App(){
 const [token,setToken]=useState(localStorage.getItem("accounting_token"));
 const [active,setActive]=useState("hajj"),[sidebarOpen,setSidebarOpen]=useState(false),[programs,setPrograms]=useState<Program[]>([]),[pilgrims,setPilgrims]=useState<Pilgrim[]>([]),[customers,setCustomers]=useState<any[]>([]),[suppliers,setSuppliers]=useState<any[]>([]),[agents,setAgents]=useState<any[]>([]),[me,setMe]=useState<any>(null),[error,setError]=useState("");
 const title=modules.find(([id])=>id===active)?.[1]??"الحج";
 useEffect(()=>{if(!token)return;Promise.allSettled([getPrograms(),getPilgrims(),getParties("customer"),getParties("supplier"),getParties("agent")]).then(r=>{if(r[0].status==="fulfilled")setPrograms(r[0].value);if(r[1].status==="fulfilled")setPilgrims(r[1].value);if(r[2].status==="fulfilled")setCustomers(r[2].value);if(r[3].status==="fulfilled")setSuppliers(r[3].value);if(r[4].status==="fulfilled")setAgents(r[4].value);});},[token]);
 function logout(){localStorage.removeItem("accounting_token");setToken(null);setMe(null)}
 async function reload(){try{const [p,g,c,s,a]=await Promise.all([getPrograms(),getPilgrims(),getParties("customer"),getParties("supplier"),getParties("agent")]);setPrograms(p);setPilgrims(g);setCustomers(c);setSuppliers(s);setAgents(a);setError("")}catch(e){setError(e instanceof Error?e.message:"تعذر تحديث البيانات")}}
 if(!token)return <LoginPage onLogin={t=>{localStorage.setItem("accounting_token",t);setToken(t)}}/>;
 return <div className="shell" dir="rtl"><aside className={sidebarOpen?"sidebar open":"sidebar"}><div className="brand"><div className="brand-mark">م</div><div><strong>وكالة مهراس</strong><span>الحج والعمرة والسفر</span></div></div><nav>{modules.map(([id,label,icon])=><button className={active===id?"nav-item active":"nav-item"} key={id} onClick={()=>{setActive(id);setSidebarOpen(false)}}><span className="nav-icon">{icon}</span>{label}</button>)}</nav><div className="sidebar-foot">نظام محاسبي متخصص • كل خدمة مرتبطة بالدليل</div></aside><section className="content"><header className="topbar"><button className="menu-toggle" onClick={()=>setSidebarOpen(v=>!v)}>☰</button><div><h1>{title}</h1><p>نظام محاسبي وتشغيلي لوكالة مهراس</p></div><div className="top-actions"><button className="icon-btn" title="تسجيل الخروج" onClick={logout}>⇥</button>{me&&<div className="user-chip"><span>م</span><div><b>{me.full_name}</b><small>{me.username}</small></div></div>}</div></header>{error&&<div className="error-banner">{error}</div>}
 {active==="hajj"&&<HajjPage programs={programs} pilgrims={pilgrims} suppliers={suppliers} customers={customers}/>} 
 {active==="umrah"&&<UmrahPage programs={programs} pilgrims={pilgrims} suppliers={suppliers} customers={customers}/>} 
 {active==="flight"&&<ServicePage serviceType="flight" title="الطيران" icon="✈️" pilgrims={pilgrims} suppliers={suppliers} customers={customers} agents={agents}/>} 
 {active==="buses"&&<ServicePage serviceType="bus" title="الباصات" icon="🚌" pilgrims={pilgrims} suppliers={suppliers} customers={customers} agents={agents}/>} 
 {active==="accounts"&&<AccountsPage/>} {active==="settings"&&<SettingsPage/>}</section></div>
}
function LoginPage({onLogin}:{onLogin:(token:string)=>void}){const [username,setUsername]=useState("admin"),[password,setPassword]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState("");async function submit(e:React.FormEvent){e.preventDefault();setBusy(true);setError("");try{const r=await login(username,password);onLogin(r.access_token)}catch(e){setError(e instanceof Error?e.message:"تعذر تسجيل الدخول")}finally{setBusy(false)}}return <div className="login-shell" dir="rtl"><form className="login-card" onSubmit={submit}><div className="brand-mark">م</div><h1>وكالة مهراس</h1><p>نظام الحج والعمرة والسفر والمحاسبة</p><label>اسم المستخدم<input value={username} onChange={e=>setUsername(e.target.value)} required/></label><label>كلمة المرور<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required/></label>{error&&<div className="error-banner">{error}</div>}<button className="primary" disabled={busy}>{busy?"جارٍ الدخول…":"دخول إلى النظام"}</button></form></div>}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App/></React.StrictMode>);
