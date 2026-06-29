"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import type {
  AmazonConnectionTestResponse,
  AmazonImportOrdersResponse,
  AmazonManualImportResponse,
  AmazonMessagingActionsResponse,
  AmazonStatus,
  AmazonSyncRun,
} from "@/types";

const categories = ["配送未到", "配送延迟", "商品破损", "商品不良", "缺件", "错发", "返品希望", "退款咨询", "使用方法", "差评风险", "其他"];

const emptyStatus: AmazonStatus = {
  stage: "v0.3.8",
  mode: "production_spapi_sync",
  auto_sync_enabled: false,
  ready_for_next_stage: false,
  credentials: {
    lwa_client_id: false,
    lwa_client_secret: false,
    refresh_token: false,
    marketplace_id: false,
    endpoint_region: "jp",
    aws_signing_ready: false,
  },
  stores: [],
  missing_items: [],
};

function BoolBadge({ ok, label }: { ok: boolean; label: string }) {
  return <span className={`badge ${ok ? "success" : "muted-badge"}`}>{label}：{ok ? "已配置" : "未配置"}</span>;
}

function formatDate(value?: string) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("zh-CN", { hour12: false });
}

export default function AmazonPage() {
  const router = useRouter();
  const [status, setStatus] = useState<AmazonStatus>(emptyStatus);
  const [syncRuns, setSyncRuns] = useState<AmazonSyncRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [checkingActions, setCheckingActions] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [testResult, setTestResult] = useState<AmazonConnectionTestResponse | null>(null);
  const [syncResult, setSyncResult] = useState<AmazonImportOrdersResponse | null>(null);
  const [actionsResult, setActionsResult] = useState<AmazonMessagingActionsResponse | null>(null);
  const [syncDays, setSyncDays] = useState(3);
  const [syncMax, setSyncMax] = useState(20);
  const [pageLimit, setPageLimit] = useState(2);
  const [actionOrderId, setActionOrderId] = useState("");
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
      const [data, runs] = await Promise.all([
        apiFetch<AmazonStatus>("/amazon/status"),
        apiFetch<AmazonSyncRun[]>("/amazon/sync-runs?limit=10"),
      ]);
      setStatus(data);
      setSyncRuns(runs);
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

  async function testConnection() {
    setError("");
    setMessage("");
    setTestResult(null);
    setTesting(true);
    try {
      const result = await apiFetch<AmazonConnectionTestResponse>("/amazon/test-connection", {
        method: "POST",
        body: JSON.stringify({ store_id: form.store_id || undefined, days: syncDays }),
      });
      setTestResult(result);
      setMessage(result.store_name ? `SP-API 连接成功：${result.store_name}` : "SP-API 连接成功。可以继续同步最近订单。");
    } catch (err) {
      setError(err instanceof Error ? `SP-API 连接失败：${err.message}` : "SP-API 连接失败。");
    } finally {
      setTesting(false);
    }
  }

  async function syncOrders() {
    setError("");
    setMessage("");
    setSyncResult(null);
    if (!form.store_id) {
      setError("请先选择一个 Amazon 店铺。");
      return;
    }
    setSyncing(true);
    try {
      const result = await apiFetch<AmazonImportOrdersResponse>("/amazon/import-orders", {
        method: "POST",
        body: JSON.stringify({ store_id: form.store_id, days: syncDays, max_results: syncMax, page_limit: pageLimit }),
      });
      setSyncResult(result);
      setMessage(`同步完成：拉取 ${result.fetched_count} 单，订单新增 ${result.order_created_count} / 更新 ${result.order_updated_count}，工作项新增 ${result.ticket_created_count} / 更新 ${result.ticket_updated_count}，跳过 ${result.skipped_count}。`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? `订单同步失败：${err.message}` : "订单同步失败。");
      try { await load(); } catch {}
    } finally {
      setSyncing(false);
    }
  }

  async function checkMessagingActions() {
    setError("");
    setMessage("");
    setActionsResult(null);
    if (!actionOrderId.trim()) {
      setError("请填写 Amazon 订单号。");
      return;
    }
    setCheckingActions(true);
    try {
      const result = await apiFetch<AmazonMessagingActionsResponse>("/amazon/messaging-actions", {
        method: "POST",
        body: JSON.stringify({ amazon_order_id: actionOrderId.trim(), store_id: form.store_id || undefined }),
      });
      setActionsResult(result);
      setMessage(`已查询可发送消息动作：${result.available_actions_count} 个。`);
    } catch (err) {
      setError(err instanceof Error ? `查询消息动作失败：${err.message}` : "查询消息动作失败。");
    } finally {
      setCheckingActions(false);
    }
  }

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
          <h2>Amazon 正式接入</h2>
          <p>v0.3.8 支持多店铺 Amazon 授权：全局应用配置与店铺 Refresh Token 分开管理，再按店铺同步订单。</p>
        </div>
        <div className="summary-pill">{status.ready_for_next_stage ? "正式接入准备完成" : "接入准备中"}</div>
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
            <BoolBadge ok={!!status.credentials.aws_signing_ready} label="AWS签名" />
          </div>
          <div className="readiness-box">
            <strong>{status.ready_for_next_stage ? "可以正式调用 SP-API" : "还不能正式调用 SP-API"}</strong>
            <p>{status.next_step || "请补齐配置。"}</p>
            <p className="muted">Endpoint：{status.credentials.endpoint || "-"} / Signing：{status.credentials.signing_region || "-"}</p>
            {status.official_limit_note && <p className="muted">注意：{status.official_limit_note}</p>}
            {!status.ready_for_next_stage && status.missing_items.length > 0 && (
              <ul>
                {status.missing_items.map(item => <li key={item}>{item}</li>)}
              </ul>
            )}
          </div>
        </section>

        <section className="card amazon-status-card">
          <h3>Amazon JP 店铺准备</h3>
          <p>至少需要一个 Amazon 店铺填写 Seller ID，并开启同步。</p>
          <table className="compact-table">
            <thead><tr><th>店铺</th><th>编码</th><th>Seller ID</th><th>Refresh Token</th><th>同步</th><th>最后同步</th><th>状态</th></tr></thead>
            <tbody>
              {status.stores.map(s => (
                <tr key={s.id}>
                  <td>{s.store_name}</td>
                  <td>{s.store_code}</td>
                  <td>{s.seller_id || <span className="muted">未填写</span>}</td>
                  <td><span className={`badge ${s.refresh_token_ready ? "success" : "muted-badge"}`}>{s.refresh_token_ready ? "已配置" : "未配置"}</span></td>
                  <td><span className={`badge ${s.amazon_sync_enabled ? "success" : "muted-badge"}`}>{s.amazon_sync_enabled ? "已启用" : "未启用"}</span></td>
                  <td>{s.last_sync_at ? formatDate(s.last_sync_at) : "-"}</td>
                  <td><span className={`badge ${s.seller_id_ready && s.refresh_token_ready && s.amazon_sync_enabled ? "success" : "muted-badge"}`}>{s.seller_id_ready && s.refresh_token_ready && s.amazon_sync_enabled ? "已准备" : "待补充"}</span></td>
                </tr>
              ))}
              {status.stores.length === 0 && <tr><td colSpan={7} className="empty-table">暂无 Amazon 店铺，请先到【店铺】新增。</td></tr>}
            </tbody>
          </table>
        </section>
      </div>

      <section className="card manual-import-card">
        <div className="section-title-row">
          <div>
            <h3>正式 SP-API 同步</h3>
            <p>先测试连接，再按店铺同步最近订单。同步会写入订单表，并自动创建或更新工作项。</p>
          </div>
          <button className="btn secondary" type="button" onClick={() => router.push("/workspace")}>去工作项中心</button>
        </div>
        <div className="amazon-import-form">
          <div className="form-row four">
            <label>同步店铺
              <select className="select" value={form.store_id} onChange={e => setForm({ ...form, store_id: Number(e.target.value) })}>
                <option value={0}>请选择店铺</option>
                {status.stores.map(s => <option key={s.id} value={s.id}>{s.store_code} - {s.store_name}</option>)}
              </select>
            </label>
            <label>最近天数
              <input className="input" type="number" min={1} max={30} value={syncDays} onChange={e => setSyncDays(Number(e.target.value || 3))} />
            </label>
            <label>每页订单数
              <input className="input" type="number" min={1} max={100} value={syncMax} onChange={e => setSyncMax(Number(e.target.value || 20))} />
            </label>
            <label>最多页数
              <input className="input" type="number" min={1} max={10} value={pageLimit} onChange={e => setPageLimit(Number(e.target.value || 1))} />
            </label>
          </div>
          <div className="button-row">
            <button className="btn secondary" type="button" disabled={testing} onClick={testConnection}>{testing ? "连接测试中..." : "测试 SP-API 连接"}</button>
            <button className="btn" type="button" disabled={syncing} onClick={syncOrders}>{syncing ? "同步中..." : "同步最近订单"}</button>
          </div>
          {testResult && <div className="error-box neutral">{testResult.message} {testResult.store_name ? `店铺：${testResult.store_name}；` : ""}最近样本订单：{testResult.sample_order_ids.join(" / ") || "无"}</div>}
          {syncResult && <div className="error-box neutral">拉取 {syncResult.fetched_count} 单；订单新增 {syncResult.order_created_count}、更新 {syncResult.order_updated_count}；工作项新增 {syncResult.ticket_created_count}、更新 {syncResult.ticket_updated_count}；跳过 {syncResult.skipped_count}。</div>}
        </div>
      </section>

      <section className="card manual-import-card">
        <div className="section-title-row">
          <div>
            <h3>同步任务记录</h3>
            <p>每次同步都会留下记录，方便确认成功、失败和数量。</p>
          </div>
          <button className="btn secondary" type="button" onClick={load}>刷新记录</button>
        </div>
        <table className="compact-table">
          <thead><tr><th>时间</th><th>状态</th><th>店铺ID</th><th>拉取</th><th>订单新增/更新</th><th>工作项新增/更新</th><th>跳过</th><th>错误</th></tr></thead>
          <tbody>
            {syncRuns.map(run => (
              <tr key={run.id}>
                <td>{formatDate(run.started_at)}</td>
                <td><span className={`badge ${run.status === "success" ? "success" : run.status === "failed" ? "danger" : "muted-badge"}`}>{run.status}</span></td>
                <td>{run.store_id || "-"}</td>
                <td>{run.fetched_count || 0}</td>
                <td>{run.order_created_count || 0} / {run.order_updated_count || 0}</td>
                <td>{run.ticket_created_count || 0} / {run.ticket_updated_count || 0}</td>
                <td>{run.skipped_count || 0}</td>
                <td>{run.error_message ? <span className="muted">{run.error_message.slice(0, 80)}</span> : "-"}</td>
              </tr>
            ))}
            {syncRuns.length === 0 && <tr><td colSpan={8} className="empty-table">暂无同步记录。</td></tr>}
          </tbody>
        </table>
      </section>

      <section className="card amazon-status-card">
        <div className="section-title-row">
          <div>
            <h3>正式配置入口</h3>
            <p>敏感密钥由超级管理员在配置中心维护；Seller ID 和同步开关在店铺管理维护。</p>
          </div>
        </div>
        <div className="permission-hint-grid">
          <div className="permission-hint-card">
            <strong>1. Amazon SP-API 密钥</strong>
            <p>LWA Client ID、Client Secret、默认 Marketplace ID、Amazon Region。</p>
            <button className="btn secondary" type="button" onClick={() => router.push("/settings/amazon")}>去 Amazon 配置</button>
          </div>
          <div className="permission-hint-card">
            <strong>2. Amazon 店铺资料</strong>
            <p>维护店铺编码、Seller ID、Marketplace ID、Refresh Token，并开启 Amazon 同步。</p>
            <button className="btn secondary" type="button" onClick={() => router.push("/stores")}>去店铺管理</button>
          </div>
          <div className="permission-hint-card">
            <strong>3. 权限说明</strong>
            <p>只有拥有 amazon.sync 的账号可以同步订单；只有配置权限账号可以维护密钥。</p>
            <button className="btn secondary" type="button" onClick={() => router.push("/settings")}>查看角色权限</button>
          </div>
        </div>
      </section>

      <section className="card manual-import-card">
        <div className="section-title-row">
          <div>
            <h3>买家消息动作检查</h3>
            <p>输入 Amazon 订单号，查询该订单当前允许发送哪些买家消息类型。此功能只查询，不发送。</p>
          </div>
        </div>
        <div className="amazon-import-form">
          <div className="form-row two">
            <label>Amazon 订单号
              <input className="input" value={actionOrderId} onChange={e => setActionOrderId(e.target.value)} placeholder="例如 123-1234567-1234567" />
            </label>
            <label>操作
              <button className="btn secondary" type="button" disabled={checkingActions} onClick={checkMessagingActions}>{checkingActions ? "查询中..." : "查询可发送消息类型"}</button>
            </label>
          </div>
          {actionsResult && <div className="error-box neutral">可用动作 {actionsResult.available_actions_count} 个：{actionsResult.available_action_titles.join(" / ") || "Amazon 未返回标题"}</div>}
        </div>
      </section>

      <section className="card manual-import-card">
        <div className="section-title-row">
          <div>
            <h3>手动导入 Amazon 买家消息</h3>
            <p>如果 Amazon 不开放站内信收件箱自动拉取，仍可把真实买家消息粘贴进来，进入同一套工作项、附件和 AI 回复流程。</p>
          </div>
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
