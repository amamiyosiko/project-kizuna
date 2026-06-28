"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import type { Store, Ticket, TicketEvent, TicketMessage } from "@/types";

const statusTabs = [
  { label: "全部", value: "" },
  { label: "新建", value: "NEW" },
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

const priorityLabel: Record<string, string> = { P1: "P1 紧急", P2: "P2 高", P3: "P3 普通", P4: "P4 低" };
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

export default function WorkspacePage() {
  const router = useRouter();
  const [stores, setStores] = useState<Store[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [messages, setMessages] = useState<TicketMessage[]>([]);
  const [events, setEvents] = useState<TicketEvent[]>([]);
  const [active, setActive] = useState<Ticket | null>(null);
  const [activeStoreId, setActiveStoreId] = useState<number | "">("");
  const [activeStatus, setActiveStatus] = useState("");
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [agentReply, setAgentReply] = useState("");
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

  async function loadTickets() {
    const params = new URLSearchParams();
    if (activeStoreId) params.set("store_id", String(activeStoreId));
    if (activeStatus) params.set("status", activeStatus);
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
      await loadTickets();
    } catch {
      router.push("/login");
    }
  }

  useEffect(() => { initialLoad(); }, []);
  useEffect(() => { loadTickets(); }, [activeStoreId, activeStatus]);

  async function openTicket(ticket: Ticket) {
    setActive(ticket);
    setAgentReply("");
    const [m, e] = await Promise.all([
      apiFetch<TicketMessage[]>(`/tickets/${ticket.id}/messages`),
      apiFetch<TicketEvent[]>(`/tickets/${ticket.id}/events`),
    ]);
    setMessages(m);
    setEvents(e);
  }

  async function refreshActive(ticketId?: number) {
    const list = await loadTickets();
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
      setForm(v => ({ ...v, buyer_name: "", order_no: "", asin: "", sku: "", subject: "", initial_message: "" }));
      await refreshActive(created.id);
    } finally {
      setBusy(false);
    }
  }

  async function updateTicketStatus(status: string) {
    if (!active) return;
    const updated = await apiFetch<Ticket>(`/tickets/${active.id}`, { method: "PATCH", body: JSON.stringify({ status }) });
    await refreshActive(updated.id);
  }

  async function updatePriority(priority: string) {
    if (!active) return;
    const updated = await apiFetch<Ticket>(`/tickets/${active.id}`, { method: "PATCH", body: JSON.stringify({ priority }) });
    await refreshActive(updated.id);
  }

  async function addAgentMessage() {
    if (!active || !agentReply.trim()) return;
    setBusy(true);
    try {
      await apiFetch<TicketMessage>(`/tickets/${active.id}/messages`, {
        method: "POST",
        body: JSON.stringify({ sender_type: "AGENT", content: agentReply.trim() }),
      });
      setAgentReply("");
      await refreshActive(active.id);
    } finally {
      setBusy(false);
    }
  }

  const storeCounts = useMemo(() => stores.map(s => ({ ...s, count: tickets.filter(t => t.store_id === s.id).length })), [stores, tickets]);
  const activeStore = active?.store_id ? storeMap.get(active.store_id) : undefined;

  return (
    <AppShell>
      <div className="ticket-workspace">
        <aside className="panel ticket-nav">
          <div className="workspace-brand">
            <strong>Ticket Workspace</strong>
            <span>生产使用版 v0.2.1</span>
          </div>
          <button className="btn full" onClick={() => setShowCreate(true)}>＋ 新建 Ticket</button>
          <input className="input" placeholder="搜索 Ticket / Buyer / 订单 / SKU" value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => { if (e.key === "Enter") loadTickets(); }} />
          <button className="btn secondary full" onClick={() => loadTickets()}>搜索</button>
          <div className="divider" />
          <button className={`store-row ${activeStoreId === "" ? "active" : ""}`} onClick={() => setActiveStoreId("")}>全部店铺 <span>{tickets.length}</span></button>
          {storeCounts.map(s => <button key={s.id} className={`store-row ${activeStoreId === s.id ? "active" : ""}`} onClick={() => setActiveStoreId(s.id)}>🟢 {s.store_code}<span>{s.count}</span></button>)}
          <div className="divider" />
          <div className="status-list">
            {statusTabs.map(t => <button key={t.label} className={activeStatus === t.value ? "active" : ""} onClick={() => setActiveStatus(t.value)}>{t.label}</button>)}
          </div>
        </aside>

        <section className="panel ticket-list-panel">
          <div className="panel-title"><h3>Tickets</h3><span>{tickets.length}</span></div>
          <div className="ticket-list-scroll">
            {tickets.map(t => {
              const s = t.store_id ? storeMap.get(t.store_id) : undefined;
              return <button key={t.id} className={`ticket-card ${active?.id === t.id ? "selected" : ""}`} onClick={() => openTicket(t)}>
                <div className="ticket-card-head"><strong>{t.buyer_name}</strong><span className={`priority ${priorityClass(t.priority)}`}>{t.priority}</span></div>
                <p>{t.subject || "Amazon Buyer Message"}</p>
                <div className="ticket-card-meta"><span>{t.ticket_no}</span><span>{s?.store_code || "-"}</span></div>
                <div className="ticket-card-meta"><span>{statusLabel[t.status || "NEW"] || t.status}</span><span>{fmtTime(t.last_message_at)}</span></div>
              </button>;
            })}
            {!tickets.length && <div className="empty-state small">暂无 Ticket。点击【+ 新建 Ticket】开始，或等待后续 Amazon 自动同步。</div>}
          </div>
        </section>

        <main className="panel ticket-main-panel">
          {active ? <>
            <div className="ticket-header">
              <div>
                <div className="ticket-no">{active.ticket_no}</div>
                <h2>{active.subject || "Amazon Buyer Message"}</h2>
                <p>{active.platform} {active.marketplace} · {activeStore?.store_code || "-"} · Buyer: {active.buyer_name}</p>
              </div>
              <div className="ticket-header-actions">
                <select className="select" value={active.status || "NEW"} onChange={e => updateTicketStatus(e.target.value)}>
                  {statusTabs.filter(s => s.value).map(s => <option value={s.value} key={s.value}>{s.label}</option>)}
                  <option value="OPEN">已打开</option>
                  <option value="WAITING_PLATFORM">等待平台</option>
                </select>
                <select className="select" value={active.priority || "P3"} onChange={e => updatePriority(e.target.value)}>
                  <option value="P1">P1 紧急</option><option value="P2">P2 高</option><option value="P3">P3 普通</option><option value="P4">P4 低</option>
                </select>
              </div>
            </div>
            <div className="ticket-context-strip">
              <div><span>订单号</span><strong>{active.order_no || "-"}</strong></div>
              <div><span>ASIN</span><strong>{active.asin || "-"}</strong></div>
              <div><span>SKU</span><strong>{active.sku || "-"}</strong></div>
              <div><span>分类</span><strong>{active.category || "-"}</strong></div>
            </div>
            <div className="ticket-message-scroll">
              {messages.map(m => <div key={m.id} className={`ticket-bubble ${m.sender_type.toLowerCase()}`}>
                <small>{m.sender_type === "CUSTOMER" ? "买家" : m.sender_type === "AGENT" ? "客服" : m.sender_type}</small>
                <div>{m.content}</div>
                <em>{fmtTime(m.created_at)}</em>
              </div>)}
              {!messages.length && <div className="empty-state small">暂无消息。</div>}
            </div>
            <div className="agent-reply-box">
              <textarea className="textarea compact" placeholder="输入客服回复，保存后会进入 Timeline。V0.2.1 先留档，自动发送到 Amazon 放到后续版本。" value={agentReply} onChange={e => setAgentReply(e.target.value)} />
              <button className="btn" disabled={busy || !agentReply.trim()} onClick={addAgentMessage}>保存客服回复</button>
            </div>
          </> : <div className="empty-state">请选择一个 Ticket，或点击左侧【+ 新建 Ticket】。</div>}
        </main>

        <aside className="panel ticket-ai-panel">
          <div className="panel-title"><h3>AI / Timeline</h3><span className="copilot-badge">Copilot</span></div>
          <div className="analysis-box v2">
            <div><span>摘要</span><strong>{active ? "待 AI 分析" : "-"}</strong></div>
            <div><span>分类</span><strong>{active?.category || "-"}</strong></div>
            <div><span>风险</span><strong>{active?.risk_level || "-"}</strong></div>
            <div><span>建议</span><strong>{active ? "先人工处理" : "-"}</strong></div>
          </div>
          <div className="timeline-box ticket-events">
            <h4>Timeline</h4>
            {events.map(ev => <div key={ev.id} className="event-row"><strong>{ev.title}</strong><p>{ev.description || ev.event_type}</p><small>{fmtTime(ev.created_at)}</small></div>)}
            {active && !events.length && <p className="muted">暂无 Timeline。</p>}
          </div>
          <div className="note-box">v0.2.1 聚焦 Ticket 基础能力。AI 回复、S3 附件预览将在后续小版本继续上线。</div>
        </aside>

        {showCreate && <div className="modal-backdrop">
          <form className="ticket-modal" onSubmit={createTicket}>
            <div className="modal-head"><h3>新建 Ticket</h3><button type="button" className="link-btn" onClick={() => setShowCreate(false)}>关闭</button></div>
            <label>店铺 *</label>
            <select className="select" value={form.store_id} onChange={e => setForm({ ...form, store_id: Number(e.target.value) })}>
              {stores.map(s => <option key={s.id} value={s.id}>{s.store_name} / {s.store_code}</option>)}
            </select>
            <label>Buyer *</label>
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
            <button className="btn full" disabled={busy || !form.store_id || !form.buyer_name.trim() || !form.initial_message.trim()}>{busy ? "保存中..." : "创建 Ticket"}</button>
          </form>
        </div>}
      </div>
    </AppShell>
  );
}
