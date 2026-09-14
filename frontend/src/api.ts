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
export type Booking = { id:number; program_id:number; pilgrim_id:number; customer_id:number|null; agent_id:number|null; quota_id:number|null; supplier_id:number|null; sale_price:string; supplier_cost:string; paid_amount:string; remaining_amount:string; profit:string; customer_type:string; status:string; journal_entry_id:number|null; booked_at:string; branch_id:number|null };
export type VisaService = { id:number; pilgrim_id:number; customer_id:number|null; supplier_id:number|null; visa_type:string; sale_price:string; supplier_cost:string; profit:string; status:string; journal_entry_id:number|null; created_at:string; branch_id:number|null };
export type HajjQuota = { id:number; name_ar:string; season:string; supplier_id:number; total_units:number; used_units:number; remaining_units:number; unit_cost:string; status:string; branch_id:number|null };
export type ServiceOrder = { id:number; service_type:string; reference_no:string; service_date:string; description:string; details:Record<string,unknown>|null; pilgrim_id:number|null; customer_id:number|null; agent_id:number|null; supplier_id:number|null; sale_price:string; supplier_cost:string; paid_amount:string; remaining_amount:string; profit:string; status:string; journal_entry_id:number|null; created_by:number|null; branch_id:number|null; created_at:string; posted_at:string|null };

const queryParams = (params?:ReportParams) => { const q = new URLSearchParams(); if(params?.from_date) q.set("from_date",params.from_date); if(params?.to_date) q.set("to_date",params.to_date); const s=q.toString(); return s?`?${s}`:""; };

export const getSettings=()=>api<Setting[]>("/settings");
export const updateSetting=(key:string,value:string)=>api<Setting>(`/settings/${encodeURIComponent(key)}`,{method:"PUT",body:JSON.stringify({value})});
export const getPrograms=()=>api<Program[]>("/travel/programs");
export const getPilgrims=()=>api<Pilgrim[]>("/travel/pilgrims");
export const getDashboard=()=>api<Dashboard>("/dashboard");
export const getBranches=()=>api<any[]>("/branches");
export const getUsers=()=>api<any[]>("/users");
export const getMe=()=>api<{id:number;username:string;full_name:string;branch_id:number|null;is_active:boolean}>("/auth/me");
export const getParties=(type?:string)=>api<any[]>(`/parties${type?`?party_type=${encodeURIComponent(type)}`:""}`);
export const createParty=(payload:any)=>api<any>("/parties",{method:"POST",body:JSON.stringify(payload)});
export const deleteParty=(id:number)=>api<any>(`/parties/${id}`,{method:"DELETE"});
export const getAccounts=()=>api<any[]>("/accounts");
export const createAccount=(payload:any)=>api<any>("/accounts",{method:"POST",body:JSON.stringify(payload)});
export const getFinancial=()=>api<any[]>("/financial-accounts");
export const createFinancial=(payload:any)=>api<any>("/financial-accounts",{method:"POST",body:JSON.stringify(payload)});
export const getCurrencies=()=>api<any[]>("/currencies");
export const createCurrency=(payload:any)=>api<any>("/currencies",{method:"POST",body:JSON.stringify(payload)});
export const getRoles=()=>api<any[]>("/users/roles");
export const createUser=(payload:any)=>api<any>("/users",{method:"POST",body:JSON.stringify(payload)});
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
export const printVoucher=async(id:number)=>{const data=await getVoucherPrintData(id);const v=data.voucher??{};const w=window.open("","_blank","width=900,height=700");if(!w)throw new Error("تعذر فتح نافذة الطباعة");w.document.write(`<html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>${v.voucher_number??"سند"}</title><style>body{font-family:Arial;margin:40px}table{width:100%;border-collapse:collapse}th,td{border:1px solid #ccc;padding:10px;text-align:right}</style></head><body><h1>وكالة مهراس</h1><h2>سند مالي ${v.voucher_number??""}</h2><p>${v.description??""}</p><table><tr><th>المبلغ</th><td>${v.amount??""}</td></tr><tr><th>الخدمة المرتبطة</th><td>${v.linked_service_type??"—"} ${v.linked_service_id??""}</td></tr><tr><th>الحالة</th><td>${v.status??""}</td></tr></table><p>طبع بواسطة: ${data.printed_by??""}</p><script>window.onload=()=>window.print()</script></body></html>`);w.document.close()};

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
export const login=(username:string,password:string)=>api<{access_token:string;token_type:string}>("/auth/login",{method:"POST",body:JSON.stringify({username,password})});
