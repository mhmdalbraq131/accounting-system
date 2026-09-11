const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

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
export type Program = { id: number; code: string; name_ar: string; program_type: string; season: string | null; departure_date: string | null; return_date: string | null; capacity: number; sale_price: string; supplier_cost: string; is_active: boolean };
export type Pilgrim = { id: number; customer_id: number | null; full_name: string; passport_number: string | null; nationality: string | null; phone: string | null; visa_status: string; };
export type Dashboard = { programs:number; pilgrims:number; bookings:number; visas:number; customers:number; suppliers:number; revenue:string; service_cost:string; gross_profit:string; expenses:string; net_profit:string; posted_journals:number };

export const getSettings = () => api<Setting[]>("/settings");
export const updateSetting = (key: string, value: string) => api<Setting>(`/settings/${encodeURIComponent(key)}`, { method: "PUT", body: JSON.stringify({ value }) });
export const getPrograms = () => api<Program[]>("/travel/programs");
export const getPilgrims = () => api<Pilgrim[]>("/travel/pilgrims");
export const getDashboard = () => api<Dashboard>("/dashboard");

export type Branch = { id:number; code:string; name_ar:string; address:string|null; phone:string|null; is_main:boolean; is_active:boolean };
export type User = { id:number; username:string; full_name:string; branch_id:number|null; is_active:boolean };
export const getBranches = () => api<Branch[]>("/branches");
export const getUsers = () => api<User[]>("/users");
export const getMe = () => api<{id:number;username:string;full_name:string;branch_id:number|null;is_active:boolean}>("/auth/me");
export const getVoucherPrintData = (id:number) => api<{voucher:unknown;printed_by:string;printed_by_username:string;branch_id:number|null}>(`/vouchers/${id}/print-data`);

export const getCurrencies = () => api<any[]>("/currencies");
export const getFinancialAccounts = () => api<any[]>("/financial-accounts");


export const createProgram = (payload: {code:string;name_ar:string;program_type:string;season?:string;capacity:number;sale_price:number;supplier_cost:number}) =>
  api<Program>("/travel/programs", {method:"POST", body:JSON.stringify(payload)});

export const createPilgrim = (payload: {full_name:string;passport_number?:string;nationality?:string;phone?:string;customer_id?:number}) =>
  api<Pilgrim>("/travel/pilgrims", {method:"POST", body:JSON.stringify(payload)});

export const createBranch = (payload: {code:string;name_ar:string;address?:string;phone?:string;is_main:boolean}) =>
  api<Branch>("/branches", {method:"POST", body:JSON.stringify(payload)});

export const createUser = (payload: {username:string;full_name:string;password:string;branch_id?:number;role_id?:number}) =>
  api<User>("/users", {method:"POST", body:JSON.stringify(payload)});

export const createParty = (payload: {name:string;party_type:string;phone?:string;address?:string;code?:string;email?:string;notes?:string;account_id?:number}) =>
  api<any>("/parties", {method:"POST", body:JSON.stringify(payload)});


export const getParties = (type?:string) => api<any[]>(`/parties${type?("?party_type="+encodeURIComponent(type)):""}`);
export const getAccounts = () => api<any[]>("/accounts");
export const getFinancial = () => api<any[]>("/financial-accounts");
export const getCurrencies = () => api<any[]>("/currencies");
export const getVouchers = () => api<any[]>("/vouchers");
export const getFinancialSummary = () => api<any>("/reports/financial-summary");
export const getVisaServices = () => api<any[]>("/travel/visas");
export const createVisa = (payload:any) => api<any>("/travel/visas",{method:"POST",body:JSON.stringify(payload)});
export const createAccount = (payload:any) => api<any>("/accounts",{method:"POST",body:JSON.stringify(payload)});
export const createFinancial = (payload:any) => api<any>("/financial-accounts",{method:"POST",body:JSON.stringify(payload)});
export const createCurrency = (payload:any) => api<any>("/currencies",{method:"POST",body:JSON.stringify(payload)});
export const createVoucher = (payload:any) => api<any>("/vouchers",{method:"POST",body:JSON.stringify(payload)});
export const postVoucher = (id:number) => api<any>(`/vouchers/${id}/post`,{method:"POST"});
export const cancelVoucher = (id:number) => api<any>(`/vouchers/${id}/cancel`,{method:"POST"});
