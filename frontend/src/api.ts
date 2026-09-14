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

export type Setting = { key: string; value: string; value_type: string; category: string; description_ar: string | null; is_editable: boolean };
export type Program = { id: number; code: string; name_ar: string; program_type: string; season: string | null; departure_date: string | null; return_date: string | null; capacity: number; sale_price: string; supplier_cost: string; supplier_id: number | null; is_active: boolean };
export type Pilgrim = { id: number; customer_id: number | null; full_name: string; passport_number: string | null; nationality: string | null; phone: string | null; visa_status: string; };
export type Dashboard = { programs:number; pilgrims:number; bookings:number; visas:number; customers:number; suppliers:number; revenue:string; service_cost:string; gross_profit:string; expenses:string; net_profit:string; posted_journals:number };
export type ReportParams = { from_date?: string; to_date?: string };
export type Booking = { id:number; program_id:number; pilgrim_id:number; customer_id:number|null; agent_id:number|null; quota_id:number|null; supplier_id:number|null; sale_price:string; supplier_cost:string; paid_amount:string; remaining_amount:string; profit:string; customer_type:string; status:string; journal_entry_id:number|null; booked_at:string; branch_id:number|null };
export type VisaService = { id:number; pilgrim_id:number; customer_id:number|null; supplier_id:number|null; visa_type:string; sale_price:string; supplier_cost:string; profit:string; status:string; journal_entry_id:number|null; created_at:string; branch_id:number|null };
export type HajjQuota = { id:number; name_ar:string; season:string; supplier_id:number; total_units:number; used_units:number; remaining_units:number; unit_cost:string; status:string; branch_id:number|null };

const queryParams = (params?: ReportParams) => {
  const query = new URLSearchParams();
  if (params?.from_date) query.set("from_date", params.from_date);
  if (params?.to_date) query.set("to_date", params.to_date);
  const value = query.toString();
  return value ? `?${value}` : "";
};

export const getSettings = () => api<Setting[]>("/settings");
export const updateSetting = (key: string, value: string) => api<Setting>(`/settings/${encodeURIComponent(key)}`, { method: "PUT", body: JSON.stringify({ value }) });
export const getPrograms = () => api<Program[]>("/travel/programs");
export const getPilgrims = () => api<Pilgrim[]>("/travel/pilgrims");
export const getBookings = () => api<Booking[]>("/travel/bookings");
export const postBooking = (id:number) => api<Booking>(`/travel/bookings/${id}/post`, { method:"POST" });
export const cancelBooking = (id:number) => api<Booking>(`/travel/bookings/${id}/cancel`, { method:"POST" });
export const getHajjQuotas = () => api<HajjQuota[]>("/hajj/quotas");
export const createHajjQuota = (payload:{name_ar:string;season:string;supplier_id:number;total_units:number;unit_cost:number}) => api<HajjQuota>("/hajj/quotas", {method:"POST", body:JSON.stringify(payload)});
export const getHajjBookings = () => api<Booking[]>("/hajj/bookings");
export const createHajjBooking = (payload:{program_id:number;pilgrim_id:number;agent_id?:number;customer_id?:number;quota_id:number;sale_price:number;supplier_cost?:number}) => api<Booking>("/hajj/bookings", {method:"POST", body:JSON.stringify(payload)});
export const postHajjBooking = (id:number) => api<Booking>(`/hajj/bookings/${id}/post`, {method:"POST"});
export const getAgentBalance = (id:number) => api<{agent_id:number;agent_name:string;debit:string;paid:string;remaining:string}>(`/hajj/agents/${id}/balance`);
export const getDashboard = () => api<Dashboard>("/dashboard");

export type Branch = { id:number; code:string; name_ar:string; address:string|null; phone:string|null; is_main:boolean; is_active:boolean };
export type User = { id:number; username:string; full_name:string; branch_id:number|null; is_active:boolean };
export const getBranches = () => api<Branch[]>("/branches");
export const getUsers = () => api<User[]>("/users");
export const getMe = () => api<{id:number;username:string;full_name:string;branch_id:number|null;is_active:boolean}>("/auth/me");
export const getVoucherPrintData = (id:number) => api<{voucher:any;printed_by:string;printed_by_username:string;branch_id:number|null}>(`/vouchers/${id}/print-data`);
export const printVoucher = async (id:number) => {
  const data = await getVoucherPrintData(id);
  const voucher = data.voucher ?? {};
  const printWindow = window.open("", "_blank", "width=900,height=700");
  if (!printWindow) throw new Error("تعذر فتح نافذة الطباعة. اسمح بالنوافذ المنبثقة ثم أعد المحاولة.");
  const typeLabel: Record<string,string> = { receipt: "سند قبض", payment: "سند صرف", transfer: "سند تحويل" };
  const escapeHtml = (value: unknown) => String(value ?? "").replace(/[&<>\"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[ch] ?? ch));
  printWindow.document.write(`<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>${escapeHtml(typeLabel[voucher.voucher_type] ?? "سند مالي")} ${escapeHtml(voucher.voucher_number)}</title><style>body{font-family:Arial,sans-serif;margin:40px;color:#111}header{display:flex;justify-content:space-between;border-bottom:2px solid #111;padding-bottom:14px;margin-bottom:24px}.meta{line-height:1.9}table{width:100%;border-collapse:collapse;margin-top:24px}th,td{border:1px solid #bbb;padding:10px;text-align:right}th{background:#f3f3f3}.amount{font-size:24px;font-weight:700}.footer{margin-top:50px;display:flex;justify-content:space-between}.muted{color:#666;font-size:12px}</style></head><body><header><div><h1>نظام المحاسبة</h1><div>وكالة الحج والعمرة والسفر</div></div><div class="meta"><b>${escapeHtml(typeLabel[voucher.voucher_type] ?? voucher.voucher_type)}</b><br>رقم السند: ${escapeHtml(voucher.voucher_number)}<br>التاريخ: ${escapeHtml(voucher.voucher_date)}</div></header><div class="meta"><b>البيان:</b> ${escapeHtml(voucher.description)}</div><table><tr><th>من الحساب</th><td>${escapeHtml(voucher.source_account_id)}</td></tr><tr><th>إلى الحساب</th><td>${escapeHtml(voucher.destination_account_id)}</td></tr><tr><th>المبلغ</th><td class="amount">${escapeHtml(voucher.amount)}</td></tr><tr><th>الخدمة المرتبطة</th><td>${escapeHtml(voucher.linked_service_type ?? "—")} ${escapeHtml(voucher.linked_service_id ?? "")}</td></tr><tr><th>الحالة</th><td>${escapeHtml(voucher.status)}</td></tr></table><div class="footer"><div>طبع بواسطة: <b>${escapeHtml(data.printed_by)}</b> (${escapeHtml(data.printed_by_username)})</div><div class="muted">رقم السند ${escapeHtml(voucher.voucher_number)}</div></div><script>window.onload=()=>{window.print();window.onafterprint=()=>window.close();}</script></body></html>`);
  printWindow.document.close();
};

export const getCurrencies = () => api<any[]>("/currencies");
export const getFinancialAccounts = () => api<any[]>("/financial-accounts");
export const createProgram = (payload: {code:string;name_ar:string;program_type:string;season?:string;capacity:number;sale_price:number;supplier_cost:number;supplier_id?:number}) => api<Program>("/travel/programs", {method:"POST", body:JSON.stringify(payload)});
export const createPilgrim = (payload: {full_name:string;passport_number?:string;nationality?:string;phone?:string;customer_id?:number}) => api<Pilgrim>("/travel/pilgrims", {method:"POST", body:JSON.stringify(payload)});
export const createBranch = (payload: {code:string;name_ar:string;address?:string;phone?:string;is_main:boolean}) => api<Branch>("/branches", {method:"POST", body:JSON.stringify(payload)});
export const createUser = (payload: {username:string;full_name:string;password:string;branch_id?:number;role_id?:number}) => api<User>("/users", {method:"POST", body:JSON.stringify(payload)});
export const createParty = (payload: {name:string;party_type:string;phone?:string;address?:string;code?:string;email?:string;notes?:string;account_id?:number}) => api<any>("/parties", {method:"POST", body:JSON.stringify(payload)});
export const getParties = (type?:string) => api<any[]>(`/parties${type?("?party_type="+encodeURIComponent(type)):""}`);
export const getAccounts = () => api<any[]>("/accounts");
export const getFinancial = () => api<any[]>("/financial-accounts");
export const getVouchers = () => api<any[]>("/vouchers");
export const getFinancialSummary = (params?: ReportParams) => api<any>(`/reports/financial-summary${queryParams(params)}`);
export const getJournalReport = (params?: ReportParams) => api<any[]>(`/reports/journal${queryParams(params)}`);
export const getLedgerReport = (accountId:number, params?: ReportParams) => api<any>(`/reports/ledger/${accountId}${queryParams(params)}`);
export const getTrialBalance = (params?: ReportParams) => api<any>(`/reports/trial-balance${queryParams(params)}`);
export const getProfitLoss = (params?: ReportParams) => api<any>(`/reports/profit-loss${queryParams(params)}`);
export const getCashMovement = (params?: ReportParams) => api<any>(`/reports/cash-movement${queryParams(params)}`);
export const getPartyReport = (partyId:number, params?: ReportParams) => api<any>(`/reports/party/${partyId}${queryParams(params)}`);
export const getVisaServices = () => api<VisaService[]>("/travel/visas");
export const createVisa = (payload:any) => api<VisaService>("/travel/visas",{method:"POST",body:JSON.stringify(payload)});
export const postVisa = (id:number) => api<VisaService>(`/travel/visas/${id}/post`,{method:"POST"});
export const cancelVisa = (id:number) => api<VisaService>(`/travel/visas/${id}/cancel`,{method:"POST"});
export const createAccount = (payload:any) => api<any>("/accounts",{method:"POST",body:JSON.stringify(payload)});
export const createFinancial = (payload:any) => api<any>("/financial-accounts",{method:"POST",body:JSON.stringify(payload)});
export const createCurrency = (payload:any) => api<any>("/currencies",{method:"POST",body:JSON.stringify(payload)});
export const createVoucher = (payload:any) => api<any>("/vouchers",{method:"POST",body:JSON.stringify(payload)});
export const postVoucher = (id:number) => api<any>(`/vouchers/${id}/post`,{method:"POST"});
export const cancelVoucher = (id:number) => api<any>(`/vouchers/${id}/cancel`,{method:"POST"});
export const getRoles = () => api<any[]>("/users/roles");
export const deleteParty = (id:number) => api<any>(`/parties/${id}`,{method:"DELETE"});
export const login = (username:string,password:string) => api<{access_token:string;token_type:string}>("/auth/login",{method:"POST",body:JSON.stringify({username,password})});
export const getExpenses = () => api<any[]>("/expenses");
export const createExpense = (payload:any) => api<any>("/expenses",{method:"POST",body:JSON.stringify(payload)});