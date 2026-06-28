"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import type { AmazonManualImportResponse, AmazonStatus } from "@/types";

const categories = ["配送未到", "配送延迟", "商品破损", "商品不良", "缺件", "错发", "返品希望", "退款咨询", "使用方法", "差评风险", "其他"];

const emptyStatus: AmazonStatus = {
  stage: "v0.3.4",
  mode: "readiness",
  auto_sync_enabled: false,
  ready_for_next_stage: false,
  credentials: {
    lwa_client_id: false,
    lwa_client_secret: false,
    refresh_token: false,
    marketplace_id: false,
    endpoint_region: "jp",
  },
  stores: [],
  missing_items: [],
};

function BoolBadge({ ok, label }: { ok: boolean; label: string }) {
  return <span className={`badge ${ok ? "success" : "muted-badge"}`}>{label}：{ok ? "已配置" : "未配置"}</span>;
}

export default function AmazonPage() {
  const router = useRouter();
  const [status, setStatus] = useState<AmazonStatus>(emptyStatus);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    store_id: 0,
    buyer_name: "",
    buyer_id: "",
    order_no: "",
    asin: "",
    sku: "",
    subject: "Amazon 买家消息",
    category: "配送未到",
    priority: "P3",
    risk_level: "low",
    message: "",
  });

  async function load() {
    setLoading(true);
    setError("");
    try {
      await apiFetch("/auth/me");
      const data = await apiFetch<AmazonStatus>("/amazon/status");
      setStatus(data);
      if (!form.store_id && data.stores[0]) {
        setForm(v => ({ ...v, store_id: data.stores[0].id }));
      }
    } catch {
      router.push("/login");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function submitManualImport(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    if (!form.store_id || !form.buyer_name.trim() || !form.message.trim()) {
      setError("请选择店铺，并填写买家名称和消息内容。");
      return;
    }
    setSaving(true);
    try {
      const result = await apiFetch<AmazonManualImportResponse>("/amazon/manual-import", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          buyer_name: form.buyer_name.trim(),
          message: form.message.trim(),
        }),
      });
      setMessage(`${result.message}：${result.ticket.ticket_no}`);
      setForm(v => ({ ...v, buyer_name: "", buyer_id: "", order_no: "", asin: "", sku: "", subject: "Amazon 买家消息", message: "" }));
    } catch (err) {
      setError(err instanceof Error ? `导入失败：${err.message}` : "导入失败，请稍后重试。");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <div className="page-header">
        <div>
          <h2>Amazon 接入</h2>
          <p>v0.3.4 先完成 SP-API 准备和手动导入链路；真实自动同步在凭证齐全后继续接入。</p>
        </div>
        <div className="summary-pill">{status.ready_for_next_stage ? "凭证准备完成" : "接入准备中"}</div>
      </div>

      <div className="amazon-grid">
        <section className="card amazon-status-card">
          <div className="section-title-row">
            <div>
              <h3>SP-API 凭证状态</h3>
              <p>这里只显示是否配置，不会显示真实密钥。</p>
            </div>
            <button className="btn secondary" type="button" onClick={load} disabled={loading}>{loading ? "刷新中..." : "刷新状态"}</button>
          </div>
          <div className="credential-badges">
            <BoolBadge ok={status.credentials.lwa_client_id} label="LWA Client ID" />
            <BoolBadge ok={status.credentials.lwa_client_secret} label="LWA Secret" />
            <BoolBadge ok={status.credentials.refresh_token} label="Refresh Token" />
            <BoolBadge ok={status.credentials.marketplace_id} label="Marketplace ID" />
          </div>
          <div className="readiness-box">
            <strong>{status.ready_for_next_stage ? "可以进入下一阶段" : "还不能自动同步"}</strong>
            <p>{status.next_step || "请补齐配置。"}</p>
            {!status.ready_for_next_stage && status.missing_items.length > 0 && (
              <ul>
                {status.missing_items.map(item => <li key={item}>{item}</li>)}
              </ul>
            )}
          </div>
        </section>

        <section className="card amazon-status-card">
          <h3>Amazon JP 店铺准备</h3>
          <p>至少需要一个 Amazon 店铺填写 Seller ID，后续同步才知道消息属于哪个店铺。</p>
          <table className="compact-table">
            <thead><tr><th>店铺</th><th>编码</th><th>Seller ID</th><th>状态</th></tr></thead>
            <tbody>
              {status.stores.map(s => (
                <tr key={s.id}>
                  <td>{s.store_name}</td>
                  <td>{s.store_code}</td>
                  <td>{s.seller_id || <span className="muted">未填写</span>}</td>
                  <td><span className={`badge ${s.seller_id_ready ? "success" : "muted-badge"}`}>{s.seller_id_ready ? "已准备" : "待补充"}</span></td>
                </tr>
              ))}
              {status.stores.length === 0 && <tr><td colSpan={4} className="empty-table">暂无 Amazon 店铺，请先到【店铺】新增。</td></tr>}
            </tbody>
          </table>
        </section>
      </div>

      <section className="card manual-import-card">
        <div className="section-title-row">
          <div>
            <h3>手动导入 Amazon 买家消息</h3>
            <p>在自动同步完成前，可以先把真实买家消息粘贴进来，验证工作项、附件和 AI 回复流程。</p>
          </div>
          <button className="btn secondary" type="button" onClick={() => router.push("/workspace")}>去工作项中心</button>
        </div>
        <form className="amazon-import-form" onSubmit={submitManualImport}>
          <div className="form-row two">
            <label>店铺
              <select className="select" value={form.store_id} onChange={e => setForm({ ...form, store_id: Number(e.target.value) })}>
                <option value={0}>请选择店铺</option>
                {status.stores.map(s => <option key={s.id} value={s.id}>{s.store_code} - {s.store_name}</option>)}
              </select>
            </label>
            <label>买家名称
              <input className="input" value={form.buyer_name} onChange={e => setForm({ ...form, buyer_name: e.target.value })} placeholder="例如：Amazon Buyer" />
            </label>
          </div>
          <div className="form-row three">
            <label>订单号
              <input className="input" value={form.order_no} onChange={e => setForm({ ...form, order_no: e.target.value })} placeholder="Amazon Order ID" />
            </label>
            <label>ASIN
              <input className="input" value={form.asin} onChange={e => setForm({ ...form, asin: e.target.value })} placeholder="ASIN" />
            </label>
            <label>SKU
              <input className="input" value={form.sku} onChange={e => setForm({ ...form, sku: e.target.value })} placeholder="SKU" />
            </label>
          </div>
          <div className="form-row three">
            <label>分类
              <select className="select" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
                {categories.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
            <label>优先级
              <select className="select" value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}>
                <option value="P1">P1 紧急</option><option value="P2">P2 高</option><option value="P3">P3 普通</option><option value="P4">P4 低</option>
              </select>
            </label>
            <label>风险
              <select className="select" value={form.risk_level} onChange={e => setForm({ ...form, risk_level: e.target.value })}>
                <option value="low">低</option><option value="medium">中</option><option value="high">高</option>
              </select>
            </label>
          </div>
          <label>主题
            <input className="input" value={form.subject} onChange={e => setForm({ ...form, subject: e.target.value })} />
          </label>
          <label>买家消息原文
            <textarea className="textarea" value={form.message} onChange={e => setForm({ ...form, message: e.target.value })} placeholder="粘贴 Amazon 买家消息，建议保留日文/英文原文。" />
          </label>
          {error && <div className="error-box">{error}</div>}
          {message && <div className="error-box neutral">{message}</div>}
          <div className="button-row">
            <button className="btn" disabled={saving}>{saving ? "导入中..." : "导入为工作项"}</button>
          </div>
        </form>
      </section>
    </AppShell>
  );
}
