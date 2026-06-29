"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import type { Store } from "@/types";

type StoreForm = {
  store_name: string;
  store_code: string;
  marketplace_id: string;
  seller_id: string;
  amazon_sync_enabled: boolean;
  status: string;
  note: string;
};

const emptyForm: StoreForm = {
  store_name: "",
  store_code: "",
  marketplace_id: "A1VC38T7YXB528",
  seller_id: "",
  amazon_sync_enabled: false,
  status: "active",
  note: ""
};

const statusOptions = [
  { value: "active", label: "启用" },
  { value: "disabled", label: "停用" }
];

export default function StoresPage() {
  const router = useRouter();
  const [stores, setStores] = useState<Store[]>([]);
  const [form, setForm] = useState<StoreForm>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [keyword, setKeyword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const filteredStores = useMemo(() => {
    const q = keyword.trim().toLowerCase();
    if (!q) return stores;
    return stores.filter(s =>
      [s.store_name, s.store_code, s.seller_id, s.note]
        .filter(Boolean)
        .some(v => String(v).toLowerCase().includes(q))
    );
  }, [stores, keyword]);

  async function load() {
    try {
      await apiFetch("/auth/me");
      setStores(await apiFetch<Store[]>("/stores"));
    } catch {
      router.push("/login");
    }
  }

  useEffect(() => { load(); }, []);

  function resetForm() {
    setForm(emptyForm);
    setEditingId(null);
    setError("");
    setMessage("");
  }

  function editStore(store: Store) {
    setEditingId(store.id);
    setForm({
      store_name: store.store_name || "",
      store_code: store.store_code || "",
      marketplace_id: store.marketplace_id || "A1VC38T7YXB528",
      seller_id: store.seller_id || "",
      amazon_sync_enabled: Boolean(store.amazon_sync_enabled),
      status: store.status || "active",
      note: store.note || ""
    });
    setError("");
    setMessage(`正在编辑：${store.store_code}`);
  }

  async function saveStore(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const payload = { ...form, platform: "Amazon", marketplace: "JP" };
      if (editingId) {
        await apiFetch(`/stores/${editingId}`, { method: "PUT", body: JSON.stringify(payload) });
        setMessage("店铺已保存。");
      } else {
        await apiFetch("/stores", { method: "POST", body: JSON.stringify(payload) });
        setMessage("店铺已新增。");
      }
      resetForm();
      await load();
    } catch (err) {
      setError("保存失败：店铺编码不能重复，且店铺名称/编码不能为空。");
    } finally {
      setLoading(false);
    }
  }

  async function toggleStatus(store: Store) {
    const nextStatus = store.status === "active" ? "disabled" : "active";
    await apiFetch(`/stores/${store.id}`, { method: "PUT", body: JSON.stringify({ status: nextStatus }) });
    await load();
  }

  async function removeStore(store: Store) {
    const ok = window.confirm(`确认删除店铺 ${store.store_code} 吗？\n如果这个店铺已经有关联消息，建议先停用，不建议删除。`);
    if (!ok) return;
    try {
      await apiFetch(`/stores/${store.id}`, { method: "DELETE" });
      if (editingId === store.id) resetForm();
      await load();
    } catch {
      setError("删除失败：可能已有会话/订单关联。建议改为停用。 ");
    }
  }

  return (
    <AppShell>
      <div className="page-header">
        <div>
          <h2>店铺管理</h2>
          <p>V1 只管理 Amazon JP 店铺；后续 Amazon 同步会使用这里的 Seller ID、Marketplace ID 和同步开关。</p>
        </div>
        <div className="summary-pill">共 {stores.length} 家店铺</div>
      </div>

      <div className="store-layout">
        <section className="card store-form-card">
          <h3>{editingId ? "编辑店铺" : "新增店铺"}</h3>
          <form className="form-stack" onSubmit={saveStore}>
            <label>店铺名称</label>
            <input className="input" placeholder="例如：Amazon JP 01" value={form.store_name} onChange={e => setForm({ ...form, store_name: e.target.value })} required />

            <label>店铺编码</label>
            <input className="input" placeholder="例如：JP01" value={form.store_code} onChange={e => setForm({ ...form, store_code: e.target.value.toUpperCase() })} required />

            <label>Marketplace ID</label>
            <input className="input" placeholder="日本站默认 A1VC38T7YXB528" value={form.marketplace_id} onChange={e => setForm({ ...form, marketplace_id: e.target.value })} />

            <label>Seller ID</label>
            <input className="input" placeholder="Amazon Seller ID" value={form.seller_id} onChange={e => setForm({ ...form, seller_id: e.target.value })} />

            <label>Amazon 同步</label>
            <select className="select" value={form.amazon_sync_enabled ? "true" : "false"} onChange={e => setForm({ ...form, amazon_sync_enabled: e.target.value === "true" })}>
              <option value="false">关闭</option>
              <option value="true">启用</option>
            </select>

            <label>状态</label>
            <select className="select" value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
              {statusOptions.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>

            <label>备注</label>
            <textarea className="textarea compact" placeholder="例如：主账号 / 负责人 / 特殊售后规则" value={form.note} onChange={e => setForm({ ...form, note: e.target.value })} />

            {error && <div className="error-box">{error}</div>}
            {message && <div className="error-box neutral">{message}</div>}

            <div className="button-row">
              <button className="btn" disabled={loading}>{loading ? "保存中..." : editingId ? "保存修改" : "新增店铺"}</button>
              {editingId && <button className="btn secondary" type="button" onClick={resetForm}>取消编辑</button>}
            </div>
          </form>
        </section>

        <section className="card store-table-card">
          <div className="table-toolbar">
            <div>
              <h3>Amazon JP 店铺</h3>
              <p>建议店铺编码使用 JP01、JP02 这种固定格式，后续消息和附件路径都会使用它。</p>
            </div>
            <input className="input search-input" placeholder="搜索店铺名称 / 编码 / Seller ID" value={keyword} onChange={e => setKeyword(e.target.value)} />
          </div>

          <table>
            <thead>
              <tr>
                <th>店铺</th>
                <th>编码</th>
                <th>平台</th>
                <th>站点</th>
                <th>Marketplace ID</th>
                <th>Seller ID</th>
                <th>同步</th>
                <th>状态</th>
                <th>备注</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredStores.map(store => (
                <tr key={store.id}>
                  <td><strong>{store.store_name}</strong></td>
                  <td>{store.store_code}</td>
                  <td>{store.platform}</td>
                  <td>{store.marketplace}</td>
                  <td>{store.marketplace_id || "A1VC38T7YXB528"}</td>
                  <td>{store.seller_id || <span className="muted">未绑定</span>}</td>
                  <td><span className={`badge ${store.amazon_sync_enabled ? "success" : "muted-badge"}`}>{store.amazon_sync_enabled ? "启用" : "关闭"}</span></td>
                  <td><span className={`badge ${store.status === "active" ? "success" : "muted-badge"}`}>{store.status === "active" ? "启用" : "停用"}</span></td>
                  <td className="note-cell">{store.note}</td>
                  <td>
                    <div className="table-actions">
                      <button className="link-btn" onClick={() => editStore(store)}>编辑</button>
                      <button className="link-btn" onClick={() => toggleStatus(store)}>{store.status === "active" ? "停用" : "启用"}</button>
                      <button className="link-btn danger" onClick={() => removeStore(store)}>删除</button>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredStores.length === 0 && (
                <tr><td colSpan={10} className="empty-table">暂无店铺。请先新增一个 Amazon JP 店铺。</td></tr>
              )}
            </tbody>
          </table>
        </section>
      </div>
    </AppShell>
  );
}
