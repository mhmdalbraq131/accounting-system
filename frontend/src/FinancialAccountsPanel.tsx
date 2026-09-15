import React, { useEffect, useState } from "react";
import { createFinancial, getAccounts, getBranches, getCurrencies, getFinancial, updateFinancial } from "./api";

const TYPES = [
  ["cashbox", "صندوق"],
  ["bank", "بنك"],
  ["wallet", "محفظة إلكترونية"],
] as const;

const labels: Record<string, string> = Object.fromEntries(TYPES);

export default function FinancialAccountsPanel() {
  const [rows, setRows] = useState<any[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [currencies, setCurrencies] = useState<any[]>([]);
  const [branches, setBranches] = useState<any[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: "",
    account_type: "cashbox",
    ledger_account_id: "",
    currency_id: "",
    opening_balance: "0",
    branch_id: "",
    is_active: true,
  });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function refresh() {
    try {
      const [financial, ledger, currencyRows, branchRows] = await Promise.all([
        getFinancial(),
        getAccounts(),
        getCurrencies(),
        getBranches(),
      ]);
      setRows(financial);
      setAccounts(ledger);
      setCurrencies(currencyRows);
      setBranches(branchRows);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "تعذر تحميل الصناديق والبنوك والمحافظ");
    }
  }

  useEffect(() => { void refresh(); }, []);

  function reset() {
    setEditingId(null);
    setForm({ name: "", account_type: "cashbox", ledger_account_id: "", currency_id: "", opening_balance: "0", branch_id: "", is_active: true });
  }

  function startEdit(row: any) {
    setEditingId(row.id);
    setForm({
      name: row.name ?? "",
      account_type: row.account_type ?? "cashbox",
      ledger_account_id: String(row.ledger_account_id ?? ""),
      currency_id: row.currency_id == null ? "" : String(row.currency_id),
      opening_balance: String(row.opening_balance ?? "0"),
      branch_id: row.branch_id == null ? "" : String(row.branch_id),
      is_active: Boolean(row.is_active),
    });
    setMessage("");
    setError("");
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      const payload = {
        name: form.name,
        account_type: form.account_type,
        ledger_account_id: Number(form.ledger_account_id),
        currency_id: form.currency_id ? Number(form.currency_id) : null,
        opening_balance: Number(form.opening_balance || 0),
        branch_id: form.branch_id ? Number(form.branch_id) : null,
        is_active: form.is_active,
      };
      if (editingId) {
        await updateFinancial(editingId, payload);
        setMessage("تم تعديل الحساب المالي");
      } else {
        await createFinancial(payload);
        setMessage("تمت إضافة الحساب المالي");
      }
      reset();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "تعذر حفظ الحساب المالي");
    }
  }

  return (
    <section className="panel" style={{ marginTop: 20 }}>
      <div className="panel-head">
        <div>
          <h3>الصناديق والبنوك والمحافظ</h3>
          <p>خطوة واحدة بسيطة: اختر النوع، الاسم، الحساب المحاسبي، العملة، والرصيد الافتتاحي. ويمكن تكرار نفس البنك بأكثر من عملة كحسابات مالية منفصلة.</p>
        </div>
      </div>
      {(error || message) && <div className={error ? "error-banner" : "notice-banner"}>{error || message}</div>}

      <div className="stats compact" style={{ marginBottom: 18 }}>
        {TYPES.map(([key, label]) => (
          <div className="stat" key={key}>
            <span>{label}</span>
            <strong>{rows.filter((r) => r.account_type === key).length}</strong>
          </div>
        ))}
      </div>

      <form className="form-grid" onSubmit={save}>
        <label>
          <span>النوع</span>
          <select value={form.account_type} onChange={(e) => setForm({ ...form, account_type: e.target.value })}>
            {TYPES.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select>
        </label>
        <label><span>الاسم</span><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder={form.account_type === "bank" ? "مثال: بنك التضامن" : form.account_type === "wallet" ? "مثال: محفظة جوال" : "مثال: صندوق فرع ذمار"} required /></label>
        <label>
          <span>الحساب المحاسبي (الأستاذ)</span>
          <select value={form.ledger_account_id} onChange={(e) => setForm({ ...form, ledger_account_id: e.target.value })} required>
            <option value="">اختر الحساب الأب/المرتبط...</option>
            {accounts.filter((a) => a.is_active && a.account_type === "asset").map((a) => <option key={a.id} value={a.id}>{a.code} - {a.name_ar}</option>)}
          </select>
        </label>
        <label>
          <span>العملة</span>
          <select value={form.currency_id} onChange={(e) => setForm({ ...form, currency_id: e.target.value })}>
            <option value="">اختر العملة...</option>
            {currencies.filter((c) => c.is_active).map((c) => <option key={c.id} value={c.id}>{c.code} - {c.name_ar}{c.is_base ? " (رسمية)" : ""}</option>)}
          </select>
        </label>
        <label><span>الرصيد الافتتاحي</span><input type="number" min="0" step="0.01" value={form.opening_balance} onChange={(e) => setForm({ ...form, opening_balance: e.target.value })} /></label>
        <label>
          <span>الفرع</span>
          <select value={form.branch_id} onChange={(e) => setForm({ ...form, branch_id: e.target.value })}>
            <option value="">نطاق الوكالة / الرئيسي</option>
            {branches.map((b) => <option key={b.id} value={b.id}>{b.name_ar}</option>)}
          </select>
        </label>
        <label>
          <span>الحالة</span>
          <select value={form.is_active ? "true" : "false"} onChange={(e) => setForm({ ...form, is_active: e.target.value === "true" })}>
            <option value="true">نشط</option><option value="false">موقوف</option>
          </select>
        </label>
        <div className="form-actions">
          <button className="primary" type="submit">{editingId ? "حفظ التعديل" : "إضافة"}</button>
          {editingId && <button type="button" onClick={reset}>إلغاء</button>}
        </div>
      </form>

      <div className="table-wrap" style={{ marginTop: 18 }}>
        <table>
          <thead><tr><th>النوع</th><th>الاسم</th><th>الحساب المحاسبي</th><th>العملة</th><th>الرصيد الافتتاحي</th><th>الفرع</th><th>الحالة</th><th>إجراء</th></tr></thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{labels[row.account_type] || row.account_type}</td>
                <td>{row.name}</td>
                <td>{accounts.find((a) => a.id === row.ledger_account_id)?.code || row.ledger_account_id || "—"}</td>
                <td>{currencies.find((c) => c.id === row.currency_id)?.code || "—"}</td>
                <td>{Number(row.opening_balance || 0).toLocaleString("ar-YE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td>{branches.find((b) => b.id === row.branch_id)?.name_ar || "رئيسي"}</td>
                <td>{row.is_active ? "نشط" : "موقوف"}</td>
                <td><button onClick={() => startEdit(row)}>تعديل</button></td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={8}>لا توجد صناديق أو بنوك أو محافظ مضافة بعد.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}
