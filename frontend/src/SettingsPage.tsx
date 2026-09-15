import React, { useEffect, useMemo, useState } from "react";
import {
  createBranch,
  createCurrency,
  createUser,
  getAccounts,
  getBranches,
  getCurrencies,
  getPermissions,
  getRolePermissions,
  getRoles,
  getSettings,
  getUsers,
  updateBranch,
  updateRolePermissions,
  updateSetting,
  updateUser,
  type ManagedUser,
  type Permission,
  type Role,
  type Setting,
} from "./api";

const ACCOUNT_KEYS = new Set([
  "travel_revenue_account_id",
  "travel_cost_account_id",
  "visa_revenue_account_id",
  "visa_cost_account_id",
  "flight_revenue_account_id",
  "flight_cost_account_id",
  "bus_revenue_account_id",
  "bus_cost_account_id",
  "visit_revenue_account_id",
  "visit_cost_account_id",
  "work_visa_revenue_account_id",
  "work_visa_cost_account_id",
]);

const groupLabel = (c: string) =>
  ({
    company: "بيانات الوكالة",
    financial: "الإعدادات المالية",
    travel: "إعدادات السفر",
    travel_accounting: "ربط الحج والعمرة والتأشيرات بالمحاسبة",
    service_accounting: "ربط الطيران والباصات والزيارات وفيز العمل بالمحاسبة",
    interface: "الواجهة",
  }[c] || c);

type ExtraService = "visit" | "work_visa";

type BranchForm = {
  code: string;
  name_ar: string;
  address: string;
  phone: string;
  is_main: boolean;
  is_active: boolean;
};

type UserForm = {
  username: string;
  full_name: string;
  password: string;
  branch_id: string;
  role_id: string;
  is_active: boolean;
};

const emptyBranch: BranchForm = {
  code: "",
  name_ar: "",
  address: "",
  phone: "",
  is_main: false,
  is_active: true,
};

const emptyUser: UserForm = {
  username: "",
  full_name: "",
  password: "",
  branch_id: "",
  role_id: "",
  is_active: true,
};

export default function SettingsPage({
  onOpenExtraService,
}: {
  onOpenExtraService?: (kind: ExtraService) => void;
} = {}) {
  const [tab, setTab] = useState("general");
  const [settings, setSettings] = useState<Setting[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [branches, setBranches] = useState<any[]>([]);
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [currencies, setCurrencies] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function refresh() {
    try {
      const [s, a, b, u, r] = await Promise.all([
        getSettings(),
        getAccounts(),
        getBranches(),
        getUsers(),
        getRoles(),
      ]);
      setSettings(s);
      setAccounts(a);
      setBranches(b);
      setUsers(u);
      setRoles(r);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "تعذر تحميل إعدادات النظام");
    }
  }

  useEffect(() => {
    refresh();
    getCurrencies().then(setCurrencies).catch(() => undefined);
  }, []);

  const grouped = useMemo(
    () => settings.reduce<Record<string, Setting[]>>((acc, s) => {
      (acc[s.category] ??= []).push(s);
      return acc;
    }, {}),
    [settings]
  );

  async function saveSetting(key: string, value: string) {
    try {
      const x = await updateSetting(key, value);
      setSettings((xs) => xs.map((s) => (s.key === key ? x : s)));
      setMessage("تم حفظ الإعداد");
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "تعذر حفظ الإعداد");
    }
  }

  const tabs = [
    ["general", "الإعدادات العامة"],
    ["accounts", "ربط الحسابات"],
    ["branches", "الفروع"],
    ["users", "المستخدمون"],
    ["roles", "الأدوار والصلاحيات"],
    ["currencies", "العملات"],
    ["extras", "الخدمات الإضافية"],
  ];

  return (
    <main className="page">
      <div className="welcome">
        <div>
          <span className="eyebrow">الإعدادات</span>
          <h2>مركز إدارة وكالة مهراس</h2>
          <p>إدارة بيانات الوكالة والفروع والمستخدمين والأدوار والصلاحيات والعملة وربط الخدمات بالمحاسبة.</p>
        </div>
      </div>

      {(error || message) && <div className={error ? "error-banner" : "notice-banner"}>{error || message}</div>}

      <div className="quick-grid" style={{ marginBottom: 20 }}>
        {tabs.map(([v, l]) => (
          <button
            className={tab === v ? "quick-btn active" : "quick-btn"}
            key={v}
            onClick={() => {
              setTab(v);
              setMessage("");
              setError("");
            }}
          >
            <b>{l}</b>
            <small>إدارة كاملة</small>
          </button>
        ))}
      </div>

      {tab === "general" && (
        <>
          {Object.entries(grouped).map(([category, items]) => (
            <section className="panel settings-panel" key={category}>
              <div className="panel-head">
                <div>
                  <h3>{groupLabel(category)}</h3>
                  <p>القيم التي يسمح بها النظام تحفظ مباشرة، والإعدادات غير القابلة للتعديل تبقى مقفلة.</p>
                </div>
              </div>
              <div className="settings-grid">
                {items
                  .filter((s) => !ACCOUNT_KEYS.has(s.key))
                  .map((s) => (
                    <SettingField key={s.key} setting={s} accounts={[]} onSave={saveSetting} />
                  ))}
              </div>
            </section>
          ))}
        </>
      )}

      {tab === "accounts" && (
        <section className="panel">
          <div className="panel-head">
            <div>
              <h3>ربط الحسابات الافتراضية</h3>
              <p>اختيار الحساب من الدليل بدل إدخال رقم الحساب يدويًا.</p>
            </div>
          </div>
          <div className="settings-grid">
            {settings
              .filter((s) => ACCOUNT_KEYS.has(s.key))
              .map((s) => (
                <SettingField key={s.key} setting={s} accounts={accounts} onSave={saveSetting} />
              ))}
          </div>
        </section>
      )}

      {tab === "branches" && <BranchesTab branches={branches} onSaved={refresh} onError={setError} onMessage={setMessage} />}
      {tab === "users" && <UsersTab users={users} branches={branches} roles={roles} onSaved={refresh} onError={setError} onMessage={setMessage} />}
      {tab === "roles" && <RolesTab roles={roles} permissions={permissions} setPermissions={setPermissions} onError={setError} onMessage={setMessage} />}
      {tab === "currencies" && <CurrenciesTab currencies={currencies} onSaved={async () => setCurrencies(await getCurrencies())} />}

      {tab === "extras" && (
        <section className="panel">
          <div className="panel-head">
            <div>
              <h3>الخدمات الإضافية</h3>
              <p>الزيارات وفيز العمل لا تظهر كوحدات رئيسية، وتُفتح من هنا مع استخدام محرك الخدمة والمورد والتحصيل نفسه.</p>
            </div>
          </div>
          <div className="quick-grid">
            <button className="quick-btn" onClick={() => onOpenExtraService?.("visit")}><span>🗺️</span><b>الزيارات</b><small>فتح إدارة الزيارات</small></button>
            <button className="quick-btn" onClick={() => onOpenExtraService?.("work_visa")}><span>🪪</span><b>فيز العمل</b><small>فتح إدارة فيز العمل</small></button>
          </div>
        </section>
      )}
    </main>
  );
}

function SettingField({
  setting,
  accounts,
  onSave,
}: {
  setting: Setting;
  accounts: any[];
  onSave: (k: string, v: string) => Promise<void>;
}) {
  const [value, setValue] = useState(setting.value);
  useEffect(() => setValue(setting.value), [setting.value]);
  const isAccount = ACCOUNT_KEYS.has(setting.key);
  return (
    <label>
      <span>{setting.description_ar || setting.key}</span>
      {isAccount ? (
        <select
          value={value}
          disabled={!setting.is_editable}
          onChange={(e) => {
            setValue(e.target.value);
            void onSave(setting.key, e.target.value);
          }}
        >
          <option value="">اختر الحساب...</option>
          {accounts.filter((a) => a.is_active).map((a) => (
            <option key={a.id} value={a.id}>{a.code} - {a.name_ar}</option>
          ))}
        </select>
      ) : setting.value_type === "boolean" ? (
        <select
          value={value}
          disabled={!setting.is_editable}
          onChange={(e) => {
            setValue(e.target.value);
            void onSave(setting.key, e.target.value);
          }}
        >
          <option value="true">نعم</option>
          <option value="false">لا</option>
        </select>
      ) : (
        <input
          value={value}
          disabled={!setting.is_editable}
          onChange={(e) => setValue(e.target.value)}
          onBlur={async () => {
            if (value !== setting.value && setting.is_editable) await onSave(setting.key, value);
          }}
        />
      )}
    </label>
  );
}

function BranchesTab({
  branches,
  onSaved,
  onError,
  onMessage,
}: {
  branches: any[];
  onSaved: () => Promise<void>;
  onError: (v: string) => void;
  onMessage: (v: string) => void;
}) {
  const [f, setF] = useState<BranchForm>(emptyBranch);
  const [editingId, setEditingId] = useState<number | null>(null);

  function startEdit(branch: any) {
    setEditingId(branch.id);
    setF({
      code: branch.code ?? "",
      name_ar: branch.name_ar ?? "",
      address: branch.address ?? "",
      phone: branch.phone ?? "",
      is_main: Boolean(branch.is_main),
      is_active: Boolean(branch.is_active),
    });
  }

  function reset() {
    setEditingId(null);
    setF(emptyBranch);
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (editingId) {
        await updateBranch(editingId, f);
        onMessage("تم تعديل بيانات الفرع");
      } else {
        await createBranch(f);
        onMessage("تم إنشاء الفرع");
      }
      onError("");
      reset();
      await onSaved();
    } catch (e) {
      onError(e instanceof Error ? e.message : "تعذر حفظ الفرع");
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h3>الفروع</h3>
          <p>يمكن للمدير تعديل رمز الفرع واسمه وعنوانه وهاتفه وحالته وتحديد الفرع الرئيسي.</p>
        </div>
      </div>
      <form className="form-grid" onSubmit={save}>
        <label><span>رمز الفرع</span><input value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} required /></label>
        <label><span>اسم الفرع</span><input value={f.name_ar} onChange={(e) => setF({ ...f, name_ar: e.target.value })} required /></label>
        <label><span>العنوان</span><input value={f.address} onChange={(e) => setF({ ...f, address: e.target.value })} /></label>
        <label><span>الهاتف</span><input value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} /></label>
        <label><span>الحالة</span><select value={f.is_active ? "true" : "false"} onChange={(e) => setF({ ...f, is_active: e.target.value === "true" })}><option value="true">نشط</option><option value="false">موقوف</option></select></label>
        <label><span>الفرع الرئيسي</span><select value={f.is_main ? "true" : "false"} onChange={(e) => setF({ ...f, is_main: e.target.value === "true" })}><option value="false">لا</option><option value="true">نعم</option></select></label>
        <div className="form-actions">
          <button className="primary">{editingId ? "حفظ تعديل الفرع" : "إضافة الفرع"}</button>
          {editingId && <button type="button" onClick={reset}>إلغاء التعديل</button>}
        </div>
      </form>
      <SimpleTable
        rows={branches}
        columns={["code", "name_ar", "address", "phone", "is_main", "is_active"]}
        labels={{ code: "الرمز", name_ar: "الفرع", address: "العنوان", phone: "الهاتف", is_main: "رئيسي", is_active: "الحالة" }}
        actions={(row) => <button onClick={() => startEdit(row)}>تعديل</button>}
        format={(column, row) => column === "is_active" ? (row[column] ? "نشط" : "موقوف") : column === "is_main" ? (row[column] ? "نعم" : "لا") : undefined}
      />
    </section>
  );
}

function UsersTab({
  users,
  branches,
  roles,
  onSaved,
  onError,
  onMessage,
}: {
  users: ManagedUser[];
  branches: any[];
  roles: Role[];
  onSaved: () => Promise<void>;
  onError: (v: string) => void;
  onMessage: (v: string) => void;
}) {
  const [f, setF] = useState<UserForm>(emptyUser);
  const [editingId, setEditingId] = useState<number | null>(null);

  function startEdit(user: ManagedUser) {
    const role = roles.find((r) => user.role_names.includes(r.name));
    setEditingId(user.id);
    setF({
      username: user.username,
      full_name: user.full_name,
      password: "",
      branch_id: user.branch_id?.toString() ?? "",
      role_id: role?.id.toString() ?? "",
      is_active: user.is_active,
    });
  }

  function reset() {
    setEditingId(null);
    setF(emptyUser);
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (editingId) {
        await updateUser(editingId, {
          username: f.username,
          full_name: f.full_name,
          password: f.password || undefined,
          branch_id: f.branch_id ? Number(f.branch_id) : null,
          role_id: f.role_id ? Number(f.role_id) : null,
          is_active: f.is_active,
        });
        onMessage("تم تعديل بيانات المستخدم");
      } else {
        if (!f.password) throw new Error("كلمة المرور مطلوبة عند إنشاء مستخدم");
        await createUser({
          username: f.username,
          full_name: f.full_name,
          password: f.password,
          branch_id: f.branch_id ? Number(f.branch_id) : undefined,
          role_id: f.role_id ? Number(f.role_id) : undefined,
        });
        onMessage("تم إنشاء المستخدم");
      }
      onError("");
      reset();
      await onSaved();
    } catch (e) {
      onError(e instanceof Error ? e.message : "تعذر حفظ المستخدم");
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h3>المستخدمون</h3>
          <p>المدير يستطيع تعديل الاسم والفرع والدور والحالة، وتغيير كلمة المرور عند الحاجة.</p>
        </div>
      </div>
      <form className="form-grid" onSubmit={save}>
        <label><span>اسم المستخدم</span><input value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} required /></label>
        <label><span>الاسم</span><input value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} required /></label>
        <label><span>{editingId ? "كلمة مرور جديدة (اختياري)" : "كلمة المرور"}</span><input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} minLength={8} required={!editingId} /></label>
        <label><span>الفرع</span><select value={f.branch_id} onChange={(e) => setF({ ...f, branch_id: e.target.value })}><option value="">كل الفروع</option>{branches.map((b) => <option key={b.id} value={b.id}>{b.name_ar}</option>)}</select></label>
        <label><span>الدور</span><select value={f.role_id} onChange={(e) => setF({ ...f, role_id: e.target.value })}><option value="">بدون دور</option>{roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}</select></label>
        <label><span>الحالة</span><select value={f.is_active ? "true" : "false"} onChange={(e) => setF({ ...f, is_active: e.target.value === "true" })}><option value="true">نشط</option><option value="false">موقوف</option></select></label>
        <div className="form-actions">
          <button className="primary">{editingId ? "حفظ تعديل المستخدم" : "إضافة المستخدم"}</button>
          {editingId && <button type="button" onClick={reset}>إلغاء التعديل</button>}
        </div>
      </form>
      <SimpleTable
        rows={users}
        columns={["username", "full_name", "branch_id", "role_names", "is_active"]}
        labels={{ username: "المستخدم", full_name: "الاسم", branch_id: "الفرع", role_names: "الأدوار", is_active: "الحالة" }}
        actions={(row) => <button onClick={() => startEdit(row)}>تعديل</button>}
        format={(column, row) => column === "is_active" ? (row[column] ? "نشط" : "موقوف") : column === "role_names" ? (row[column]?.join("، ") || "—") : column === "branch_id" ? (branches.find((b) => b.id === row[column])?.name_ar || "كل الفروع") : undefined}
      />
    </section>
  );
}

function RolesTab({
  roles,
  permissions,
  setPermissions,
  onError,
  onMessage,
}: {
  roles: Role[];
  permissions: Permission[];
  setPermissions: React.Dispatch<React.SetStateAction<Permission[]>>;
  onError: (v: string) => void;
  onMessage: (v: string) => void;
}) {
  const [roleId, setRoleId] = useState<number | null>(roles[0]?.id ?? null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!roleId) return;
    setLoading(true);
    Promise.all([getPermissions(), getRolePermissions(roleId)])
      .then(([all, current]) => {
        setPermissions(all);
        setSelected(new Set(current.map((p) => p.code)));
        onError("");
      })
      .catch((e) => onError(e instanceof Error ? e.message : "تعذر تحميل صلاحيات الدور"))
      .finally(() => setLoading(false));
  }, [roleId, setPermissions, onError]);

  async function save() {
    if (!roleId) return;
    try {
      await updateRolePermissions(roleId, Array.from(selected));
      onMessage("تم حفظ صلاحيات الدور");
      onError("");
    } catch (e) {
      onError(e instanceof Error ? e.message : "تعذر حفظ صلاحيات الدور");
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h3>الأدوار والصلاحيات</h3>
          <p>كل دور يحصل على صلاحيات محددة، ويمكن للمدير ضبطها دون تعديل الكود.</p>
        </div>
      </div>
      <label style={{ display: "block", maxWidth: 360, marginBottom: 18 }}>
        <span>الدور</span>
        <select value={roleId ?? ""} onChange={(e) => setRoleId(e.target.value ? Number(e.target.value) : null)}>
          <option value="">اختر الدور...</option>
          {roles.map((role) => <option key={role.id} value={role.id}>{role.name}</option>)}
        </select>
      </label>
      {loading ? <div className="notice-banner">جاري تحميل الصلاحيات...</div> : (
        <div className="settings-grid">
          {permissions.map((permission) => (
            <label key={permission.code} className="panel" style={{ margin: 0 }}>
              <span>{permission.name_ar}</span>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <input
                  type="checkbox"
                  checked={selected.has(permission.code)}
                  onChange={(e) => {
                    const next = new Set(selected);
                    if (e.target.checked) next.add(permission.code); else next.delete(permission.code);
                    setSelected(next);
                  }}
                />
                <code>{permission.code}</code>
              </div>
            </label>
          ))}
        </div>
      )}
      <div className="form-actions" style={{ marginTop: 18 }}><button className="primary" onClick={save} disabled={!roleId || loading}>حفظ صلاحيات الدور</button></div>
    </section>
  );
}

function CurrenciesTab({ currencies, onSaved }: { currencies: any[]; onSaved: () => Promise<void> }) {
  const [f, setF] = useState({ code: "", name_ar: "", symbol: "" });
  const [error, setError] = useState("");
  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createCurrency(f);
      setF({ code: "", name_ar: "", symbol: "" });
      setError("");
      await onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "تعذر إنشاء العملة");
    }
  }
  return (
    <section className="panel">
      <div className="panel-head"><div><h3>العملات</h3><p>العملة الأساسية وأسعار الصرف تأتي ضمن الإعدادات المالية.</p></div></div>
      {error && <div className="error-banner">{error}</div>}
      <form className="form-grid" onSubmit={save}>
        <label><span>الرمز</span><input value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} required /></label>
        <label><span>اسم العملة</span><input value={f.name_ar} onChange={(e) => setF({ ...f, name_ar: e.target.value })} required /></label>
        <label><span>الرمز المختصر</span><input value={f.symbol} onChange={(e) => setF({ ...f, symbol: e.target.value })} required /></label>
        <div className="form-actions"><button className="primary">إضافة العملة</button></div>
      </form>
      <SimpleTable rows={currencies} columns={["code", "name_ar", "symbol", "is_base", "is_active"]} labels={{ code: "الرمز", name_ar: "العملة", symbol: "الرمز", is_base: "أساسية", is_active: "الحالة" }} format={(column, row) => column === "is_active" || column === "is_base" ? (row[column] ? "نعم" : "لا") : undefined} />
    </section>
  );
}

function SimpleTable({
  rows,
  columns,
  labels,
  actions,
  format,
}: {
  rows: any[];
  columns: string[];
  labels: Record<string, string>;
  actions?: (row: any) => React.ReactNode;
  format?: (column: string, row: any) => string | undefined;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{columns.map((c) => <th key={c}>{labels[c] || c}</th>)}{actions && <th>إجراء</th>}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id ?? i}>
              {columns.map((c) => <td key={c}>{format?.(c, r) ?? r[c] ?? "—"}</td>)}
              {actions && <td>{actions(r)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
