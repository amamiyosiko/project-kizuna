"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import type { Attachment, PresignUploadResponse, Store, Ticket, TicketEvent, TicketMessage, TicketStats } from "@/types";

const statusTabs = [
  { label: "全部", value: "" },
  { label: "新建", value: "NEW" },
  { label: "已打开", value: "OPEN" },
  { label: "处理中", value: "PROCESSING" },
  { label: "等待客户", value: "WAITING_CUSTOMER" },
  { label: "已解决", value: "RESOLVED" },
  { label: "已关闭", value: "CLOSED" },
];

const statusLabel: Record<string, string> = {
  NEW: "新建",
  OPEN: "已打开",
  PROCESSING: "处理中",
  WAITING_CUSTOMER: "等待客户",
  WAITING_PLATFORM: "等待平台",
  RESOLVED: "已解决",
  CLOSED: "已关闭",
};

const riskLabel: Record<string, string> = { low: "低", medium: "中", high: "高" };
const categories = ["配送未到", "配送延迟", "商品破损", "商品不良", "缺件", "错发", "返品希望", "退款咨询", "使用方法", "差评风险", "其他"];

function fmtTime(value?: string) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function priorityClass(priority?: string) {
  if (priority === "P1") return "p1";
  if (priority === "P2") return "p2";
  if (priority === "P4") return "p4";
  return "p3";
}

function senderLabel(sender: string) {
  if (sender === "CUSTOMER") return "买家";
  if (sender === "AGENT") return "客服";
  if (sender === "AI") return "AI";
  if (sender === "SYSTEM") return "系统";
  return sender;
}

function formatFileSize(size?: number) {
  if (!size) return "0 KB";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function isPreviewImage(att: Attachment) {
  return !!att.file_url && !!att.content_type && att.content_type.startsWith("image/");
}

const emptyStats: TicketStats = {
  total: 0,
  new: 0,
  open: 0,
  processing: 0,
  waiting_customer: 0,
  waiting_platform: 0,
  resolved: 0,
  closed: 0,
  p1: 0,
  p2: 0,
  high_risk: 0,
  today_created: 0,
};

export default function WorkspacePage() {
  const router = useRouter();
  const [stores, setStores] = useState<Store[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [messages, setMessages] = useState<TicketMessage[]>([]);
  const [events, setEvents] = useState<TicketEvent[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [stats, setStats] = useState<TicketStats>(emptyStats);
  const [active, setActive] = useState<Ticket | null>(null);
  const [activeStoreId, setActiveStoreId] = useState<number | "">("");
  const [activeStatus, setActiveStatus] = useState("");
  const [activePriority, setActivePriority] = useState("");
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [agentReply, setAgentReply] = useState("");
  const [customerMessage, setCustomerMessage] = useState("");
  const [form, setForm] = useState({
    store_id: 0,
    buyer_name: "",
    order_no: "",
    asin: "",
    sku: "",
    subject: "",
    category: "配送未到",
    priority: "P3",
    risk_level: "low",
    initial_message: "",
  });

  const storeMap = useMemo(() => new Map(stores.map(s => [s.id, s])), [stores]);

  async function loadStats() {
    const data = await apiFetch<TicketStats>("/tickets/stats/summary");
    setStats(data);
  }

  async function loadTickets() {
    const params = new URLSearchParams();
    if (activeStoreId) params.set("store_id", String(activeStoreId));
    if (activeStatus) params.set("status", activeStatus);
    if (activePriority) params.set("priority", activePriority);
    if (search.trim()) params.set("q", search.trim());
    const data = await apiFetch<Ticket[]>(`/tickets${params.toString() ? `?${params.toString()}` : ""}`);
    setTickets(data);
    return data;
  }

  async function initialLoad() {
    try {
      await apiFetch("/auth/me");
      const s = await apiFetch<Store[]>("/stores");
      setStores(s);
      if (s[0]) setForm(v => ({ ...v, store_id: v.store_id || s[0].id }));
      await Promise.all([loadTickets(), loadStats()]);
    } catch {
      router.push("/login");
    }
  }

  useEffect(() => { initialLoad(); }, []);
  useEffect(() => { loadTickets(); }, [activeStoreId, activeStatus, activePriority]);

  async function openTicket(ticket: Ticket) {
    setActive(ticket);
    setAgentReply("");
    setCustomerMessage("");
    const [m, e, a] = await Promise.all([
      apiFetch<TicketMessage[]>(`/tickets/${ticket.id}/messages`),
      apiFetch<TicketEvent[]>(`/tickets/${ticket.id}/events`),
      apiFetch<Attachment[]>(`/attachments/tickets/${ticket.id}`),
    ]);
    setMessages(m);
    setEvents(e);
    setAttachments(a);
  }

  async function refreshActive(ticketId?: number) {
    const [list] = await Promise.all([loadTickets(), loadStats()]);
    const id = ticketId || active?.id;
    const latest = list.find(t => t.id === id);
    if (latest) await openTicket(latest);
  }

  async function createTicket(e: React.FormEvent) {
    e.preventDefault();
    if (!form.store_id || !form.buyer_name.trim() || !form.initial_message.trim()) return;
    setBusy(true);
    try {
      const created = await apiFetch<Ticket>("/tickets", {
        method: "POST",
        body: JSON.stringify({ ...form, buyer_name: form.buyer_name.trim(), initial_message: form.initial_message.trim() }),
      });
      setShowCreate(false);
      setActiveStatus("");
      setActivePriority("");
      setForm(v => ({ ...v, buyer_name: "", order_no: "", asin: "", sku: "", subject: "", initial_message: "" }));
      await refreshActive(created.id);
    } finally {
      setBusy(false);
    }
  }

  async function updateTicket(payload: Partial<Ticket>) {
    if (!active) return;
    const updated = await apiFetch<Ticket>(`/tickets/${active.id}`, { method: "PATCH", body: JSON.stringify(payload) });
    await refreshActive(updated.id);
  }

  async function addMessage(senderType: "AGENT" | "CUSTOMER") {
    if (!active) return;
    const content = senderType === "AGENT" ? agentReply.trim() : customerMessage.trim();
    if (!content) return;
    setBusy(true);
    try {
      await apiFetch<TicketMessage>(`/tickets/${active.id}/messages`, {
        method: "POST",
        body: JSON.stringify({ sender_type: senderType, content }),
      });
      if (senderType === "AGENT") setAgentReply("");
      if (senderType === "CUSTOMER") setCustomerMessage("");
      await refreshActive(active.id);
    } finally {
      setBusy(false);
    }
  }

  async function uploadAttachment(file?: File) {
    if (!active || !file) return;
    setUploadBusy(true);
    try {
      const contentType = file.type || "application/octet-stream";
      const presign = await apiFetch<PresignUploadResponse>(`/attachments/tickets/${active.id}/presign`, {
        method: "POST",
        body: JSON.stringify({ file_name: file.name, content_type: contentType, file_size: file.size }),
      });
      const uploaded = await fetch(presign.upload_url, {
        method: "PUT",
        headers: { "Content-Type": contentType },
        body: file,
      });
      if (!uploaded.ok) throw new Error("S3 upload failed");
      await apiFetch<Attachment>(`/attachments/tickets/${active.id}/confirm`, {
        method: "POST",
        body: JSON.stringify({
          file_name: file.name,
          content_type: contentType,
          file_size: file.size,
          bucket: presign.bucket,
          object_key: presign.object_key,
        }),
      });
      await refreshActive(active.id);
    } finally {
      setUploadBusy(false);
    }
  }

  const storeCounts = useMemo(() => stores.map(s => ({ ...s, count: tickets.filter(t => t.store_id === s.id).length })), [stores, tickets]);
  const activeStore = active?.store_id ? storeMap.get(active.store_id) : undefined;

  return (
    <AppShell>
      <div className="ticket-workspace v031">
        <aside className="panel ticket-nav">
          <div className="workspace-brand">
            <strong>工作项中心</strong>
            <span>生产使用版 v0.3.2</span>
          </div>
          <button className="btn full" onClick={() => setShowCreate(true)}>＋ 新建工作项</button>
          <input className="input" placeholder="搜索编号 / 买家 / 订单 / SKU" value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => { if (e.key === "Enter") loadTickets(); }} />
          <button className="btn secondary full" onClick={() => loadTickets()}>搜索</button>

          <div className="workspace-stats-mini">
            <div><span>全部</span><strong>{stats.total}</strong></div>
            <div><span>今日新增</span><strong>{stats.today_created}</strong></div>
            <div><span>P1</span><strong>{stats.p1}</strong></div>
            <div><span>高风险</span><strong>{stats.high_risk}</strong></div>
          </div>

          <div className="divider" />
          <button className={`store-row ${activeStoreId === "" ? "active" : ""}`} onClick={() => setActiveStoreId("")}>全部店铺 <span>{tickets.length}</span></button>
          {storeCounts.map(s => <button key={s.id} className={`store-row ${activeStoreId === s.id ? "active" : ""}`} onClick={() => setActiveStoreId(s.id)}>🟢 {s.store_code}<span>{s.count}</span></button>)}

          <div className="divider" />
          <label className="filter-label">状态</label>
          <div className="status-list">
            {statusTabs.map(t => <button key={t.label} className={activeStatus === t.value ? "active" : ""} onClick={() => setActiveStatus(t.value)}>{t.label}</button>)}
          </div>
          <label className="filter-label top-gap">优先级</label>
          <select className="select" value={activePriority} onChange={e => setActivePriority(e.target.value)}>
            <option value="">全部优先级</option>
            <option value="P1">P1 紧急</option>
            <option value="P2">P2 高</option>
            <option value="P3">P3 普通</option>
            <option value="P4">P4 低</option>
          </select>
        </aside>

        <section className="panel ticket-list-panel">
          <div className="panel-title"><h3>工作项列表</h3><span>{tickets.length}</span></div>
          <div className="ticket-list-scroll">
            {tickets.map(t => {
              const s = t.store_id ? storeMap.get(t.store_id) : undefined;
              return <button key={t.id} className={`ticket-card ${active?.id === t.id ? "selected" : ""}`} onClick={() => openTicket(t)}>
                <div className="ticket-card-head"><strong>{t.buyer_name}</strong><span className={`priority ${priorityClass(t.priority)}`}>{t.priority}</span></div>
                <p>{t.subject || "Amazon 买家消息"}</p>
                <div className="ticket-card-meta"><span>{t.ticket_no}</span><span>{s?.store_code || "-"}</span></div>
                <div className="ticket-card-meta"><span>{statusLabel[t.status || "NEW"] || t.status}</span><span>{fmtTime(t.last_message_at)}</span></div>
              </button>;
            })}
            {!tickets.length && <div className="empty-state small">暂无工作项。点击【+ 新建工作项】开始，或等待后续 Amazon 自动同步。</div>}
          </div>
        </section>

        <main className="panel ticket-main-panel">
          {active ? <>
            <div className="ticket-header">
              <div>
                <div className="ticket-no">{active.ticket_no}</div>
                <h2>{active.subject || "Amazon 买家消息"}</h2>
                <p>{active.platform} {active.marketplace} · {activeStore?.store_code || "-"} · Buyer: {active.buyer_name}</p>
              </div>
              <div className="ticket-header-actions">
                <select className="select" value={active.status || "NEW"} onChange={e => updateTicket({ status: e.target.value })}>
                  {statusTabs.filter(s => s.value).map(s => <option value={s.value} key={s.value}>{s.label}</option>)}
                  <option value="WAITING_PLATFORM">等待平台</option>
                </select>
                <select className="select" value={active.priority || "P3"} onChange={e => updateTicket({ priority: e.target.value })}>
                  <option value="P1">P1 紧急</option><option value="P2">P2 高</option><option value="P3">P3 普通</option><option value="P4">P4 低</option>
                </select>
              </div>
            </div>

            <div className="ticket-context-strip">
              <div><span>订单号</span><strong>{active.order_no || "-"}</strong></div>
              <div><span>ASIN</span><strong>{active.asin || "-"}</strong></div>
              <div><span>SKU</span><strong>{active.sku || "-"}</strong></div>
              <div><span>分类</span><strong>{active.category || "-"}</strong></div>
              <div><span>附件</span><strong>{attachments.length}</strong></div>
            </div>

            <div className="status-flow">
              <button onClick={() => updateTicket({ status: "PROCESSING" })} disabled={active.status === "PROCESSING"}>开始处理</button>
              <button onClick={() => updateTicket({ status: "WAITING_CUSTOMER" })} disabled={active.status === "WAITING_CUSTOMER"}>等待客户</button>
              <button onClick={() => updateTicket({ status: "RESOLVED" })} disabled={active.status === "RESOLVED"}>标记解决</button>
              <button onClick={() => updateTicket({ status: "CLOSED" })} disabled={active.status === "CLOSED"}>关闭</button>
            </div>

            <div className="ticket-message-scroll">
              {messages.map(m => <div key={m.id} className={`ticket-bubble ${m.sender_type.toLowerCase()}`}>
                <small>{senderLabel(m.sender_type)}</small>
                <div>{m.content}</div>
                <em>{fmtTime(m.created_at)}</em>
              </div>)}
              {!messages.length && <div className="empty-state small">暂无消息。</div>}
            </div>

            <div className="agent-reply-box stacked">
              <textarea className="textarea compact" placeholder="输入客服回复。当前版本先保存到时间线；真正发送到 Amazon 放在 SP-API 阶段。" value={agentReply} onChange={e => setAgentReply(e.target.value)} />
              <button className="btn" disabled={busy || !agentReply.trim()} onClick={() => addMessage("AGENT")}>保存客服回复</button>
            </div>
          </> : <div className="empty-state">请选择一个工作项，或点击左侧【+ 新建工作项】。</div>}
        </main>

        <aside className="panel ticket-ai-panel">
          <div className="panel-title"><h3>详情 / 时间轴</h3><span className="copilot-badge">Core</span></div>
          <div className="analysis-box v2">
            <div><span>状态</span><strong>{active ? statusLabel[active.status || "NEW"] || active.status : "-"}</strong></div>
            <div><span>优先级</span><strong>{active?.priority || "-"}</strong></div>
            <div><span>风险</span><strong>{active ? riskLabel[active.risk_level || "low"] || active.risk_level : "-"}</strong></div>
            <div><span>负责人</span><strong>{active?.assigned_user_id || "未分配"}</strong></div>
          </div>

          {active && <div className="detail-edit-box">
            <label>分类</label>
            <select className="select" value={active.category || ""} onChange={e => updateTicket({ category: e.target.value })}>
              <option value="">未分类</option>
              {categories.map(c => <option key={c}>{c}</option>)}
            </select>
            <label>风险等级</label>
            <select className="select" value={active.risk_level || "low"} onChange={e => updateTicket({ risk_level: e.target.value })}>
              <option value="low">低</option>
              <option value="medium">中</option>
              <option value="high">高</option>
            </select>
          </div>}

          {active && <div className="attachment-box">
            <div className="attachment-head">
              <label>附件</label>
              <span>{attachments.length} 个文件</span>
            </div>
            <label className="upload-drop">
              <input type="file" disabled={uploadBusy} onChange={e => { uploadAttachment(e.target.files?.[0]); e.currentTarget.value = ""; }} />
              <strong>{uploadBusy ? "上传中..." : "上传到 S3"}</strong>
              <small>支持图片、PDF、文本等文件；用于保存买家截图、破损照片、标签图。</small>
            </label>
            <div className="attachment-list">
              {attachments.map(att => <div className="attachment-item" key={att.id}>
                {isPreviewImage(att) ? <img src={att.file_url} alt={att.file_name} /> : <div className="file-icon">📎</div>}
                <div>
                  <strong title={att.file_name}>{att.file_name}</strong>
                  <span>{att.content_type || "file"} · {formatFileSize(att.file_size)}</span>
                  {att.file_url && <a href={att.file_url} target="_blank" rel="noreferrer">打开 / 下载</a>}
                </div>
              </div>)}
              {!attachments.length && <p className="muted">暂无附件。</p>}
            </div>
          </div>}

          {active && <div className="customer-message-box">
            <label>记录买家追加消息</label>
            <textarea className="textarea compact" placeholder="如果客户再次回复，可以先手动记录到时间线。" value={customerMessage} onChange={e => setCustomerMessage(e.target.value)} />
            <button className="btn secondary full" disabled={busy || !customerMessage.trim()} onClick={() => addMessage("CUSTOMER")}>保存买家消息</button>
          </div>}

          <div className="timeline-box ticket-events">
            <h4>操作时间轴</h4>
            {events.map(ev => <div key={ev.id} className="event-row"><strong>{ev.title}</strong><p>{ev.description || ev.event_type}</p><small>{fmtTime(ev.created_at)}</small></div>)}
            {active && !events.length && <p className="muted">暂无时间轴。</p>}
            {!active && <p className="muted">选择工作项后显示操作记录。</p>}
          </div>
          <div className="note-box">v0.3.2 增加 S3 附件上传、附件列表、图片预览和下载链接；仍然只围绕工作项中心推进。</div>
        </aside>

        {showCreate && <div className="modal-backdrop">
          <form className="ticket-modal" onSubmit={createTicket}>
            <div className="modal-head"><h3>新建工作项</h3><button type="button" className="link-btn" onClick={() => setShowCreate(false)}>关闭</button></div>
            <label>店铺 *</label>
            <select className="select" value={form.store_id} onChange={e => setForm({ ...form, store_id: Number(e.target.value) })}>
              {stores.map(s => <option key={s.id} value={s.id}>{s.store_name} / {s.store_code}</option>)}
            </select>
            <label>买家 *</label>
            <input className="input" value={form.buyer_name} onChange={e => setForm({ ...form, buyer_name: e.target.value })} placeholder="例如 山田太郎" />
            <label>订单号</label>
            <input className="input" value={form.order_no} onChange={e => setForm({ ...form, order_no: e.target.value })} placeholder="Amazon 订单号，可空" />
            <div className="modal-grid">
              <div><label>ASIN</label><input className="input" value={form.asin} onChange={e => setForm({ ...form, asin: e.target.value })} /></div>
              <div><label>SKU</label><input className="input" value={form.sku} onChange={e => setForm({ ...form, sku: e.target.value })} /></div>
            </div>
            <label>主题</label>
            <input className="input" value={form.subject} onChange={e => setForm({ ...form, subject: e.target.value })} placeholder="例如 配送について" />
            <div className="modal-grid">
              <div><label>分类</label><select className="select" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>{categories.map(c => <option key={c}>{c}</option>)}</select></div>
              <div><label>优先级</label><select className="select" value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}><option value="P1">P1 紧急</option><option value="P2">P2 高</option><option value="P3">P3 普通</option><option value="P4">P4 低</option></select></div>
            </div>
            <label>买家消息 *</label>
            <textarea className="textarea" value={form.initial_message} onChange={e => setForm({ ...form, initial_message: e.target.value })} placeholder="粘贴 Amazon 买家消息内容" />
            <button className="btn full" disabled={busy || !form.store_id || !form.buyer_name.trim() || !form.initial_message.trim()}>{busy ? "保存中..." : "创建工作项"}</button>
          </form>
        </div>}
      </div>
    </AppShell>
  );
}
