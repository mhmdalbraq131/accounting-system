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
export type Pilgrim = { id: number; customer_id: number | null; full_name: string; passport_number: string; nationality: string | null; phone: string | null; visa_status: string; };

export const getSettings = () => api<Setting[]>("/settings");
export const updateSetting = (key: string, value: string) => api<Setting>(`/settings/${encodeURIComponent(key)}`, { method: "PUT", body: JSON.stringify({ value }) });
export const getPrograms = () => api<Program[]>("/travel/programs");
export const getPilgrims = () => api<Pilgrim[]>("/travel/pilgrims");
