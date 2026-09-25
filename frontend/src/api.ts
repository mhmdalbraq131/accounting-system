const API_BASE = import.meta.env.VITE_API_URL ?? `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("accounting_token");
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    let message = `تعذر تنفيذ العملية (${response.status})`;
    try { const body = await response.json(); message = body.detail ?? message; } catch { /* ignore */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export type Setting = { key:string; value:string; value_type:string; category:string; description_ar:string|null; is_editable:boolean };
export type Program = { id:number; code:string; name_ar:string; program_type:string; season:string|null; departure_date:string|null; return_date:string|null; capacity:number; sale_price:string; supplier_cost:string; supplier_id:number|null; is_active:boolean };
export type Pilgrim = { id:number; customer_id:number|null; full_name:string; passport_number:string|null; nationality:string|null; phone:string|null; visa_status:string };
export type Dashboard = { programs:number; pilgrims:number; bookings:number; visas:number; customers:number; suppliers:number; revenue:string; service_cost:string; gross_profit:string; expenses:string; net_profit:string; posted_journals:number };
export type ReportParams = { from_date?:string; to_date?:string };
export type Booking = { id:number; program_id:number; pilgrim_id:number; customer_id:number|null; agent_id:number|null; quota_id:number|null; supplier_id:number|null; sale_price:string; supplier_cost:string; paid_amount:string; remaining_amount:string; profit:string; customer_type:string; status:string; journal_entry_id:number|null; booked_at:string; branch_id:number|null; supplier_paid_amount?:string };
export type VisaService = { id:number; pilgrim_id:number; customer_id:number|null; supplier_id:number|null; visa_type:string; sale_price:string; supplier_cost:string; profit:string; status:string; journal_entry_id:number|null; created_at:string; branch_id:number|null };
export type HajjQuota = { id:number; name_ar:string; season:string; supplier_id:number; total_units:number; used_units:number; remaining_units:number; unit_cost:string; status:string; branch_id:number|null };
export type ServiceOrder = { id:number; service_type:string; reference_no:string; service_date:string; description:string; details:Record<string,unknown>|null; pilgrim_id:number|null; customer_id:number|null; agent_id:number|null; supplier_id:number|null; sale_price:string; supplier_cost:string; paid_amount:string; remaining_amount:string; profit:string; status:string; journal_entry_id:number|null; created_by:number|null; branch_id:number|null; created_at:string; posted_at:string|null; supplier_paid_amount?:string };
export type Role = { id:number; name:string; is_active:boolean };
export type Permission = { id:number; code:string; name_ar:string };
export type ManagedUser = { id:number; username:string; full_name:string; branch_id:number|null; is_active:boolean; role_names:string[]; permission_codes:string[] };

const queryParams = (params?:ReportParams) => { const q = new URLSearchParams(); if(params?.from_date) q.set("from_date",params.from_date); if(params?.to_date) q.set("to_date",params.to_date); const s=q.toString(); return s?`?${s}`:""; };

export const getSettings=()=>api<Setting[]>("/settings");
export const updateSetting=(key:string,value:string)=>api<Setting>(`/settings/${encodeURIComponent(key)}`,{method:"PUT",body:JSON.stringify({value})});
export const getPrograms=()=>api<Program[]>("/travel/programs");
export const getPilgrims=()=>api<Pilgrim[]>("/travel/pilgrims");
export const getDashboard=()=>api<Dashboard>("/dashboard");
export const getBranches=()=>api<any[]>("/branches");
export const updateBranch=(id:number,payload:any)=>api<any>(`/branches/${id}`,{method:"PUT",body:JSON.stringify(payload)});
export const getUsers=()=>api<ManagedUser[]>("/users");
export const getMe=()=>api<{id:number;username:string;full_name:string;branch_id:number|null;is_active:boolean;role_names?:string[];permission_codes?:string[]}>("/auth/me");
export const getParties=(type?:string)=>api<any[]>(`/parties${type?`?party_type=${encodeURIComponent(type)}`:""}`);
export const createParty=(payload:any)=>api<any>("/parties",{method:"POST",body:JSON.stringify(payload)});
export const deleteParty=(id:number)=>api<any>(`/parties/${id}`,{method:"DELETE"});
export const getAccounts=()=>api<any[]>("/accounts");
export const createAccount=(payload:any)=>api<any>("/accounts",{method:"POST",body:JSON.stringify(payload)});
export const getFinancial=()=>api<any[]>("/financial-accounts");
export const createFinancial=(payload:any)=>api<any>("/financial-accounts",{method:"POST",body:JSON.stringify(payload)});
export const updateFinancial=(id:number,payload:any)=>api<any>(`/financial-accounts/${id}`,{method:"PUT",body:JSON.stringify(payload)});
export const getCurrencies=()=>api<any[]>("/currencies");
export const createCurrency=(payload:any)=>api<any>("/currencies",{method:"POST",body:JSON.stringify(payload)});
export const setBaseCurrency=(id:number)=>api<any>(`/currencies/${id}/set-base`,{method:"POST"});
export const createRate=(currency_id:number,rate_to_base:number)=>api<any>("/currencies/rates",{method:"POST",body:JSON.stringify({currency_id,rate_to_base})});
export const getRoles=()=>api<Role[]>("/users/roles");
export const getPermissions=()=>api<Permission[]>("/users/permissions");
export const getRolePermissions=(id:number)=>api<Permission[]>(`/users/roles/${id}/permissions`);
export const updateRolePermissions=(id:number,permission_codes:string[])=>api<{role_id:number;permission_codes:string[]}>(`/users/roles/${id}/permissions`,{method:"PUT",body:JSON.stringify({permission_codes})});
export const createUser=(payload:any)=>api<ManagedUser>("/users",{method:"POST",body:JSON.stringify(payload)});
export const updateUser=(id:number,payload:any)=>api<ManagedUser>(`/users/${id}`,{method:"PUT",body:JSON.stringify(payload)});
export const createBranch=(payload:any)=>api<any>("/branches",{method:"POST",body:JSON.stringify(payload)});
export const createPilgrim=(payload:any)=>api<Pilgrim>("/travel/pilgrims",{method:"POST",body:JSON.stringify(payload)});
export const createProgram=(payload:any)=>api<Program>("/travel/programs",{method:"POST",body:JSON.stringify(payload)});

export const getHajjQuotas=()=>api<HajjQuota[]>("/hajj/quotas");
export const createHajjQuota=(payload:{name_ar:string;season:string;supplier_id:number;total_units:number;unit_cost:number})=>api<HajjQuota>("/hajj/quotas",{method:"POST",body:JSON.stringify(payload)});
export const getHajjBookings=()=>api<Booking[]>("/hajj/bookings");
export const createHajjBooking=(payload:{program_id:number;pilgrim_id:number;agent_id?:number;customer_id?:number;quota_id:number;sale_price:number;supplier_cost?:number})=>api<Booking>("/hajj/bookings",{method:"POST",body:JSON.stringify(payload)});
export const postHajjBooking=(id:number)=>api<Booking>(`/hajj/bookings/${id}/post`,{method:"POST"});
export const cancelHajjBooking=(id:number)=>api<Booking>(`/hajj/bookings/${id}/cancel`,{method:"POST"});
export const getAgentBalance=(id:number)=>api<any>(`/hajj/agents/${id}/balance`);

export const getUmrahBookings=()=>api<Booking[]>("/umrah/bookings");
export const createUmrahBooking=(payload:{program_id:number;pilgrim_id:number;agent_id?:number;customer_id?:number;supplier_id:number;sale_price:number;supplier_cost:number})=>api<Booking>("/umrah/bookings",{method:"POST",body:JSON.stringify(payload)});
export const postUmrahBooking=(id:number)=>api<Booking>(`/umrah/bookings/${id}/post`,{method:"POST"});
export const cancelUmrahBooking=(id:number)=>api<Booking>(`/umrah/bookings/${id}/cancel`,{method:"POST"});

export const getServices=(serviceType:"flight"|"bus"|"visit"|"work_visa")=>api<ServiceOrder[]>(`/services/${serviceType}`);
export const createService=(payload:any)=>api<ServiceOrder>("/services",{method:"POST",body:JSON.stringify(payload)});
export const postService=(serviceType:string,id:number)=>api<ServiceOrder>(`/services/${serviceType}/${id}/post`,{method:"POST"});
export const cancelService=(serviceType:string,id:number)=>api<ServiceOrder>(`/services/${serviceType}/${id}/cancel`,{method:"POST"});

export const getVouchers=()=>api<any[]>("/vouchers");
export const createVoucher=(payload:any)=>api<any>("/vouchers",{method:"POST",body:JSON.stringify(payload)});
export const postVoucher=(id:number)=>api<any>(`/vouchers/${id}/post`,{method:"POST"});
export const cancelVoucher=(id:number)=>api<any>(`/vouchers/${id}/cancel`,{method:"POST"});
export const getVoucherPrintData=(id:number)=>api<any>(`/vouchers/${id}/print-data`);

const esc=(value:unknown)=>String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");
const money=(value:unknown)=>Number(value||0).toLocaleString("ar-YE",{minimumFractionDigits:2,maximumFractionDigits:2});
const settingsMap=(rows:Setting[])=>Object.fromEntries(rows.map(s=>[s.key,s.value]));
const printShell=(title:string,body:string,settings:Record<string,string>,subtitle="")=>{const company=esc(settings.company_name||"وكالة مهراس للحج والعمرة والسفر");const contact=[settings.company_phone,settings.company_address,settings.company_email,settings.company_website].filter(Boolean).map(esc).join(" • ");const showLogo=settings.print_show_logo!=="false";const showContact=settings.print_show_contact!=="false";const logo=settings.company_logo_url?.trim();const logoHtml=showLogo&&logo?`<img class="logo" src="${esc(logo)}" alt="شعار الوكالة">`:`<div class="logo-fallback">م</div>`;const contactHtml=showContact&&contact?`<div class="contact">${contact}</div>`:"";const footer=esc(settings.print_footer||"شكرًا لثقتكم بنا — نسعد بخدمتكم دائمًا");return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>${esc(title)}</title><style>@page{size:A4;margin:12mm}*{box-sizing:border-box}body{font-family:Tahoma,Arial,sans-serif;color:#172033;margin:0;background:#fff;font-size:13px}h1,h2,h3,p{margin:0}.sheet{width:100%;min-height:270mm}.brand{display:flex;align-items:center;gap:14px;border-bottom:2px solid #203a63;padding-bottom:12px}.logo{width:76px;height:76px;object-fit:contain}.logo-fallback{width:76px;height:76px;border:2px solid #203a63;border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:34px;font-weight:800;color:#203a63}.company h1{font-size:22px;color:#203a63}.company .en{font-size:11px;color:#627084;margin-top:3px}.contact{font-size:11px;color:#627084;margin-top:5px}.title{margin:18px 0 12px;padding:10px 14px;background:#eef3f9;border-right:5px solid #203a63;font-size:20px;font-weight:800}.subtitle{color:#5b687b;margin-top:-6px;margin-bottom:10px}.meta{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:10px 0 16px}.meta div{border:1px solid #d9e0e9;padding:8px;background:#fafbfd}.meta b{display:inline-block;min-width:90px;color:#203a63}.info-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:12px 0}.info{border:1px solid #d9e0e9;padding:9px}.info b{color:#203a63}.table{width:100%;border-collapse:collapse;margin-top:14px}.table th,.table td{border:1px solid #cfd7e2;padding:8px;text-align:right}.table th{background:#edf2f7;color:#203a63}.table .total td{font-weight:800;background:#f7fafc}.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:14px}.summary .box{border:1px solid #d9e0e9;padding:10px;background:#fafbfd}.summary strong{display:block;margin-top:5px;font-size:18px;color:#203a63}.signatures{display:grid;grid-template-columns:repeat(3,1fr);gap:22px;margin-top:28px}.sig{padding-top:30px;border-top:1px dotted #8793a3;text-align:center}.footer{border-top:1px solid #d9e0e9;margin-top:24px;padding-top:10px;text-align:center;color:#697588;font-size:11px}.print-time{font-size:10px;color:#8a94a3;margin-top:4px}@media print{body{print-color-adjust:exact;-webkit-print-color-adjust:exact}}</style></head><body><div class="sheet"><div class="brand">${logoHtml}<div class="company"><h1>${company}</h1><div class="en">Mahras Travel &amp; Accounting System</div>${contactHtml}</div></div><div class="title">${esc(title)}</div>${subtitle?`<div class="subtitle">${esc(subtitle)}</div>`:""}${body}<div class="footer">${footer}<div class="print-time">${new Date().toLocaleString("ar-YE")}</div></div></div><script>window.onload=()=>window.print()</script></body></html>`};
const openPrint=async(html:string)=>{const w=window.open("","_blank","width=1000,height=800");if(!w)throw new Error("تعذر فتح نافذة الطباعة");w.document.open();w.document.write(html);w.document.close()};

export const printVoucher=async(id:number)=>{const [data,settingRows,currencies,branches]=await Promise.all([getVoucherPrintData(id),getSettings(),getCurrencies(),getBranches().catch(()=>[])]);const v=data.voucher??{};const settings=settingsMap(settingRows);const currency=currencies.find((c:any)=>c.id===v.currency_id);const branch=branches.find((b:any)=>b.id===v.branch_id);const type=v.voucher_type==="receipt"?"سند قبض":v.voucher_type==="payment"?"سند صرف":"سند تحويل";const linked=v.linked_service_type?`${v.linked_service_type} #${v.linked_service_id??""}`:"غير مرتبط بخدمة";const body=`<div class="meta"><div><b>رقم السند النظامي</b>${esc(v.voucher_number)}</div><div><b>الرقم اليدوي</b>${esc(v.manual_voucher_number||"—")}</div><div><b>التاريخ</b>${esc(v.voucher_date)}</div><div><b>الفرع</b>${esc(branch?.name_ar||"الرئيسي")}</div><div><b>العملة</b>${esc(currency?.name_ar||settings.currency_name_ar||"—")} ${esc(currency?.symbol||"")}</div><div><b>الحالة</b>${esc(v.status||"")}</div></div><div class="info-grid"><div class="info"><b>البيان:</b> ${esc(v.description)}</div><div class="info"><b>الخدمة المرتبطة:</b> ${esc(linked)}</div></div><table class="table"><thead><tr><th>م</th><th>البيان</th><th>المبلغ</th></tr></thead><tbody><tr><td>1</td><td>${esc(v.description)}</td><td>${money(v.amount)}</td></tr><tr class="total"><td colspan="2">الإجمالي</td><td>${money(v.amount)}</td></tr></tbody></table><div class="info-grid"><div class="info"><b>حساب المصدر:</b> ${esc(v.source_account_id)}</div><div class="info"><b>حساب الوجهة:</b> ${esc(v.destination_account_id)}</div></div><div class="signatures"><div class="sig">المستلم / المستفيد</div><div class="sig">المراجع المالي</div><div class="sig">المعتمد</div></div><div class="print-time">طبع بواسطة: ${esc(data.printed_by||"")} (${esc(data.printed_by_username||"")})</div>`;await openPrint(printShell(type,body,settings,`المرجع النظامي: ${v.voucher_number||"—"}`));};

export const printPartyStatement=async(report:any,fromDate?:string,toDate?:string)=>{const [settingRows,currencies,branches]=await Promise.all([getSettings(),getCurrencies(),getBranches().catch(()=>[])]);const settings=settingsMap(settingRows);const baseCode=settings.currency||"YER";const currency=currencies.find((c:any)=>c.code===baseCode);const branch=branches.find((b:any)=>b.id===report.branch_id);const rows=(report.rows||[]).map((r:any,i:number)=>`<tr><td>${i+1}</td><td>${esc(r.entry_date)}</td><td>${esc(r.entry_number)}</td><td>${esc(r.service_name)}</td><td>${esc(r.description)}</td><td>${money(r.debit)}</td><td>${money(r.credit)}</td><td>${money(r.balance)}</td></tr>`).join("");const body=`<div class="meta"><div><b>الطرف</b>${esc(report.party_name)}</div><div><b>نوع الطرف</b>${esc(report.party_type)}</div><div><b>الفترة</b>${esc(fromDate||"بداية الحساب")} — ${esc(toDate||"اليوم")}</div><div><b>الفرع</b>${esc(branch?.name_ar||"كل الفروع")}</div><div><b>العملة</b>${esc(currency?.name_ar||settings.currency_name_ar||"—")} ${esc(currency?.symbol||"")}</div><div><b>الخدمة</b>${esc(report.service_name||"كل الخدمات")}</div></div><table class="table"><thead><tr><th>م</th><th>التاريخ</th><th>رقم السند/القيد</th><th>الخدمة</th><th>البيان</th><th>مدين</th><th>دائن</th><th>الرصيد</th></tr></thead><tbody>${rows||`<tr><td colspan="8">لا توجد حركات في الفترة المحددة.</td></tr>`}</tbody><tfoot><tr class="total"><td colspan="5">الإجمالي</td><td>${money(report.total_debit)}</td><td>${money(report.total_credit)}</td><td>${money(report.balance)}</td></tr></tfoot></table><div class="summary"><div class="box"><span>إجمالي المدين</span><strong>${money(report.total_debit)}</strong></div><div class="box"><span>إجمالي الدائن</span><strong>${money(report.total_credit)}</strong></div><div class="box"><span>الرصيد الحالي</span><strong>${money(report.balance)}</strong></div></div><div class="signatures"><div class="sig">إعداد التقرير</div><div class="sig">المراجع المالي</div><div class="sig">المدير</div></div><div class="print-time">طبع بواسطة: ${esc(report.printed_by||"")} (${esc(report.username||"")})</div>`;await openPrint(printShell("كشف حساب طرف",body,settings,`الخدمة: ${report.service_name||"كل الخدمات"}`));};

export const printServiceDocument=async(row:ServiceOrder)=>{const [settingRows,currencies,branches]=await Promise.all([getSettings(),getCurrencies(),getBranches().catch(()=>[])]);const settings=settingsMap(settingRows);const currency=currencies.find((c:any)=>c.code===(settings.currency||"YER"));const branch=branches.find((b:any)=>b.id===row.branch_id);const service=row.service_type==="flight"?"الطيران":row.service_type==="bus"?"الباصات":row.service_type==="visit"?"الزيارات":"فيز العمل";const details=row.details&&Object.entries(row.details).filter(([,v])=>v).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("")||`<tr><td colspan="2">لا توجد تفاصيل إضافية</td></tr>`;const body=`<div class="meta"><div><b>المرجع</b>${esc(row.reference_no)}</div><div><b>التاريخ</b>${esc(row.service_date)}</div><div><b>الفرع</b>${esc(branch?.name_ar||"الرئيسي")}</div><div><b>الحالة</b>${esc(row.status)}</div><div><b>العملة</b>${esc(currency?.name_ar||settings.currency_name_ar||"—")} ${esc(currency?.symbol||"")}</div><div><b>رقم السجل</b>${esc(row.id)}</div></div><div class="info-grid"><div class="info"><b>البيان:</b> ${esc(row.description)}</div><div class="info"><b>الطرف:</b> ${esc(row.agent_id?`وكيل #${row.agent_id}`:row.customer_id?`عميل #${row.customer_id}`:"—")}</div></div><table class="table"><thead><tr><th>النوع</th><th>التفصيل</th></tr></thead><tbody>${details}</tbody></table><table class="table"><tbody><tr><th>سعر البيع</th><td>${money(row.sale_price)}</td></tr><tr><th>تكلفة المورد</th><td>${money(row.supplier_cost)}</td></tr><tr><th>المدفوع</th><td>${money(row.paid_amount)}</td></tr><tr class="total"><th>المتبقي</th><td>${money(row.remaining_amount)}</td></tr></tbody></table><div class="signatures"><div class="sig">المستفيد</div><div class="sig">المراجع المالي</div><div class="sig">المدير</div></div>`;await openPrint(printShell(`مستند خدمة ${service}`,body,settings,`مستند تشغيلي — ${service}`));};

export const getFinancialSummary=(p?:ReportParams)=>api<any>(`/reports/financial-summary${queryParams(p)}`);
export const getJournalReport=(p?:ReportParams)=>api<any[]>(`/reports/journal${queryParams(p)}`);
export const getLedgerReport=(accountId:number,p?:ReportParams)=>api<any>(`/reports/ledger/${accountId}${queryParams(p)}`);
export const getTrialBalance=(p?:ReportParams)=>api<any>(`/reports/trial-balance${queryParams(p)}`);
export const getProfitLoss=(p?:ReportParams)=>api<any>(`/reports/profit-loss${queryParams(p)}`);
export const getCashMovement=(p?:ReportParams)=>api<any>(`/reports/cash-movement${queryParams(p)}`);
export const getPartyReport=(partyId:number,p?:ReportParams)=>api<any>(`/reports/party/${partyId}${queryParams(p)}`);
export const getPartyServiceReport=(partyId:number,serviceType="all",p?:ReportParams)=>api<any>(`/reports/party/${partyId}/services?service_type=${encodeURIComponent(serviceType)}${p?.from_date?`&from_date=${encodeURIComponent(p.from_date)}`:""}${p?.to_date?`&to_date=${encodeURIComponent(p.to_date)}`:""}`);

export const getVisaServices=()=>api<VisaService[]>("/travel/visas");
export const createVisa=(payload:any)=>api<VisaService>("/travel/visas",{method:"POST",body:JSON.stringify(payload)});
export const postVisa=(id:number)=>api<VisaService>(`/travel/visas/${id}/post`,{method:"POST"});
export const cancelVisa=(id:number)=>api<VisaService>(`/travel/visas/${id}/cancel`,{method:"POST"});
export const getExpenses=()=>api<any[]>("/expenses");
export const createExpense=(payload:any)=>api<any>("/expenses",{method:"POST",body:JSON.stringify(payload)});
export const postExpense=(id:number)=>api<any>(`/expenses/${id}/post`,{method:"POST"});
export const cancelExpense=(id:number)=>api<any>(`/expenses/${id}/cancel`,{method:"POST"});
export const login=(username:string,password:string)=>api<{access_token:string;token_type:string}>("/auth/login",{method:"POST",body:JSON.stringify({username,password})});


export type AccountingDimension = { id:number; dimension_type:string; code:string; name_ar:string; branch_id:number|null; is_active:boolean };
export type FiscalPeriod = { id:number; name:string; start_date:string; end_date:string; is_closed:boolean; branch_id:number|null };
export type AuditLog = { id:number; user_id:number|null; action:string; entity_type:string; entity_id:number|null; details:string|null; created_at:string };

export const getAccountingDimensions=()=>api<AccountingDimension[]>("/accounting-controls/dimensions");
export const createAccountingDimension=(payload:Partial<AccountingDimension>)=>api<AccountingDimension>("/accounting-controls/dimensions",{method:"POST",body:JSON.stringify(payload)});
export const disableAccountingDimension=(id:number)=>api<AccountingDimension>(`/accounting-controls/dimensions/${id}/disable`,{method:"POST"});
export const getFiscalPeriods=()=>api<FiscalPeriod[]>("/accounting-controls/periods");
export const createFiscalPeriod=(payload:Partial<FiscalPeriod>)=>api<FiscalPeriod>("/accounting-controls/periods",{method:"POST",body:JSON.stringify(payload)});
export const closeFiscalPeriod=(id:number)=>api<{id:number;is_closed:boolean}>(`/accounting-controls/periods/${id}/close`,{method:"POST"});
export const getAuditLogs=(limit=100)=>api<AuditLog[]>(`/accounting-controls/audit?limit=${limit}`);

export const getJournals=(status?:string)=>api<any[]>(`/journals${status?`?status=${encodeURIComponent(status)}`:""}`);
export const createJournal=(payload:any)=>api<any>("/journals",{method:"POST",body:JSON.stringify(payload)});
export const postJournal=(id:number)=>api<any>(`/journals/${id}/post`,{method:"POST"});
export const cancelJournal=(id:number)=>api<any>(`/journals/${id}/cancel`,{method:"POST"});


export type Invoice = {id:number;invoice_number:string;invoice_type:"sales"|"purchase";party_id:number;invoice_date:string;due_date:string|null;description:string;total_amount:string;paid_amount:string;remaining_amount:string;receivable_account_id:number;revenue_account_id:number;journal_entry_id:number|null;status:string;branch_id:number|null};
export type Payment = {id:number;payment_number:string;payment_type:"receipt"|"payment"|"transfer";party_id:number|null;payment_date:string;amount:string;allocated_amount:string;remaining_amount:string;source_account_id:number;target_account_id:number;description:string;journal_entry_id:number|null;status:string;branch_id:number|null};
export const getInvoices=(params?:{invoice_type?:string;party_id?:number;outstanding_only?:boolean})=>api<Invoice[]>(`/ar-ap/invoices?${new URLSearchParams(Object.entries(params??{}).filter(([,v])=>v!==undefined).map(([k,v])=>[k,String(v)])).toString()}`);
export const createInvoice=(payload:any)=>api<Invoice>("/ar-ap/invoices",{method:"POST",body:JSON.stringify(payload)});
export const postInvoice=(id:number)=>api<Invoice>(`/ar-ap/invoices/${id}/post`,{method:"POST"});
export const cancelInvoice=(id:number)=>api<Invoice>(`/ar-ap/invoices/${id}/cancel`,{method:"POST"});
export const getPayments=(params?:{payment_type?:string;party_id?:number})=>api<Payment[]>(`/ar-ap/payments?${new URLSearchParams(Object.entries(params??{}).filter(([,v])=>v!==undefined).map(([k,v])=>[k,String(v)])).toString()}`);
export const createPayment=(payload:any)=>api<Payment>("/ar-ap/payments",{method:"POST",body:JSON.stringify(payload)});
export const postPayment=(id:number)=>api<Payment>(`/ar-ap/payments/${id}/post`,{method:"POST"});
export const cancelPayment=(id:number)=>api<Payment>(`/ar-ap/payments/${id}/cancel`,{method:"POST"});
export const allocatePayment=(id:number,invoice_id:number,amount:number)=>api<any>(`/ar-ap/payments/${id}/allocate`,{method:"POST",body:JSON.stringify({invoice_id,amount})});
export const getAging=(invoice_type:"sales"|"purchase")=>api<any>(`/ar-ap/aging?invoice_type=${invoice_type}`);

export const getServiceProfitability=(params?:{service_type?:string;from_date?:string;to_date?:string})=>api<any>(`/reports/service-profitability?${new URLSearchParams(Object.entries(params??{}).filter(([,v])=>v).map(([k,v])=>[k,String(v)])).toString()}`);

export const reversePaymentAllocation=(paymentId:number,allocationId:number)=>api<any>(`/ar-ap/payments/${paymentId}/allocate/${allocationId}/reverse`,{method:"POST"});
