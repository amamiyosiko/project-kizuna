"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import type { Attachment, AIReply, Conversation, Message, Store } from "@/types";

const categories = ["配送未到", "配送延迟", "商品破损", "商品不良", "缺件", "错发", "返品希望", "退款咨询", "使用方法", "差评风险", "其他"];
const statusTabs = [
  { label: "全部", value: "" },
  { label: "未处理", value: "open" },
  { label: "处理中", value: "processing" },
  { label: "等待客户", value: "waiting_customer" },
  { label: "已完成", value: "done" },
];

const statusLabel: Record<string, string> = {
  open: "未处理",
  processing: "处理中",
  waiting_customer: "等待客户",
  done: "已完成",
  closed: "已关闭",
};

function riskIcon(risk?: string) {
  if (risk === "high") return "😡";
  if (risk === "medium") return "😟";
  return "🙂";
}

function riskText(risk?: string) {
  if (risk === "high") return "高";
  if (risk === "medium") return "中";
  return "低";
}

export default function WorkspacePage() {
  const router = useRouter();
  const [stores, setStores] = useState<Store[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeStoreId, setActiveStoreId] = useState<number | null>(null);
  const [activeStatus, setActiveStatus] = useState("");
  const [active, setActive] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [templates, setTemplates] = useState<ReplyTemplate[]>([]);
  const [uploading, setUploading] = useState(false);
  const [reply, setReply] = useState<AIReply | null>(null);
  const [finalReply, setFinalReply] = useState("");
  const [tone, setTone] = useState("polite");
  const [internalNote, setInternalNote] = useState("");
  const [newMsg, setNewMsg] = useState("まだ届きません。");
  const [newConv, setNewConv] = useState({ store_id: 1, subject: "配送について", category: "配送未到", risk_level: "low" });
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      await apiFetch("/auth/me");
      const [s, c, t] = await Promise.all([apiFetch<Store[]>("/stores"), apiFetch<Conversation[]>("/conversations"), apiFetch<ReplyTemplate[]>("/templates?active_only=true")]);
      setStores(s);
      setConversations(c);
      setTemplates(t);
      if (s[0]) setNewConv(v => ({ ...v, store_id: v.store_id || s[0].id }));
    } catch {
      router.push("/login");
    }
  }

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => conversations.filter(c => {
    if (activeStoreId && c.store_id !== activeStoreId) return false;
    if (activeStatus && c.status !== activeStatus) return false;
    return true;
  }), [conversations, activeStoreId, activeStatus]);

  const storeMap = useMemo(() => new Map(stores.map(s => [s.id, s])), [stores]);
  const activeStore = active?.store_id ? storeMap.get(active.store_id) : undefined;
  const matchedTemplates = useMemo(() => templates.filter(t => !active?.category || t.category === active.category).slice(0, 5), [templates, active?.category]);

  async function openConversation(c: Conversation) {
    setActive(c);
    setReply(null);
    setFinalReply("");
    setMessages(await apiFetch<Message[]>(`/conversations/${c.id}/messages`));
    setAttachments(await apiFetch<Attachment[]>(`/attachments/conversation/${c.id}`));
  }

  async function createConversation(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const c = await apiFetch<Conversation>("/conversations", {
        method: "POST",
        body: JSON.stringify({ ...newConv, initial_message: newMsg }),
      });
      await load();
      await openConversation(c);
    } finally {
      setBusy(false);
    }
  }

  async function generateReply(toneOverride?: string) {
    if (!active) return;
    const selectedTone = toneOverride || tone;
    setTone(selectedTone);
    setBusy(true);
    try {
      const r = await apiFetch<AIReply>("/ai/generate-reply", { method: "POST", body: JSON.stringify({ conversation_id: active.id, tone: selectedTone }) });
      setReply(r);
      setFinalReply(r.ai_reply_text);
    } finally {
      setBusy(false);
    }
  }


  async function uploadAttachment(file: File) {
    if (!active) return;
    setUploading(true);
    try {
      const presigned = await apiFetch<{ upload_url: string; bucket: string; object_key: string; expires_seconds: number }>("/attachments/presign", {
        method: "POST",
        body: JSON.stringify({
          conversation_id: active.id,
          file_name: file.name,
          content_type: file.type || "application/octet-stream",
          file_size: file.size,
        }),
      });
      const uploadRes = await fetch(presigned.upload_url, {
        method: "PUT",
        headers: { "Content-Type": file.type || "application/octet-stream" },
        body: file,
      });
      if (!uploadRes.ok) throw new Error("S3 上传失败，请检查 Bucket CORS、IAM 权限和环境变量。");
      const saved = await apiFetch<Attachment>("/attachments/confirm", {
        method: "POST",
        body: JSON.stringify({
          conversation_id: active.id,
          file_name: file.name,
          content_type: file.type || "application/octet-stream",
          file_size: file.size,
          bucket: presigned.bucket,
          object_key: presigned.object_key,
        }),
      });
      setAttachments(prev => [saved, ...prev]);
    } finally {
      setUploading(false);
    }
  }

  async function copyReply() {
    if (!finalReply) return;
    await navigator.clipboard?.writeText(finalReply);
    alert("已复制日语回复");
  }

  async function saveSellerReply() {
    if (!active || !finalReply.trim()) return;
    setBusy(true);
    try {
      await apiFetch<Message>(`/conversations/${active.id}/messages`, {
        method: "POST",
        body: JSON.stringify({ sender_type: "seller", content: finalReply.trim() }),
      });
      const updated = await apiFetch<Conversation>(`/conversations/${active.id}/status`, {
        method: "PUT",
        body: JSON.stringify({ status: "done" }),
      });
      await load();
      await openConversation(updated);
      setActive(updated);
    } finally {
      setBusy(false);
    }
  }

  async function updateStatus(status: string) {
    if (!active) return;
    const updated = await apiFetch<Conversation>(`/conversations/${active.id}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    });
    await load();
    setActive(updated);
  }

  return (
    <AppShell>
      <div className="workspace-grid workspace-v2">
        <aside className="panel store-panel">
          <div className="workspace-brand">
            <strong>Customer Workspace</strong>
            <span>Amazon JP</span>
          </div>
          <button className={`store-row ${activeStoreId === null ? "active" : ""}`} onClick={() => setActiveStoreId(null)}>全部店铺 <span>{conversations.length}</span></button>
          {stores.map(s => <button key={s.id} className={`store-row ${activeStoreId === s.id ? "active" : ""}`} onClick={() => setActiveStoreId(s.id)}>🟢 {s.store_code}<span>{conversations.filter(c => c.store_id === s.id).length}</span></button>)}
          <div className="divider" />
          <div className="status-list">
            {statusTabs.map(t => <button key={t.label} className={activeStatus === t.value ? "active" : ""} onClick={() => setActiveStatus(t.value)}>{t.label}</button>)}
          </div>
          <div className="divider" />
          <h4>快速录入买家消息</h4>
          <form className="mini-form" onSubmit={createConversation}>
            <select className="select" value={newConv.store_id} onChange={e => setNewConv({ ...newConv, store_id: Number(e.target.value) })}>{stores.map(s => <option value={s.id} key={s.id}>{s.store_name}</option>)}</select>
            <input className="input" placeholder="主题，例如 配送について" value={newConv.subject} onChange={e => setNewConv({ ...newConv, subject: e.target.value })} />
            <select className="select" value={newConv.category} onChange={e => setNewConv({ ...newConv, category: e.target.value })}>{categories.map(c => <option key={c}>{c}</option>)}</select>
            <select className="select" value={newConv.risk_level} onChange={e => setNewConv({ ...newConv, risk_level: e.target.value })}>
              <option value="low">低风险</option><option value="medium">中风险</option><option value="high">高风险</option>
            </select>
            <textarea className="textarea compact" value={newMsg} onChange={e => setNewMsg(e.target.value)} />
            <button className="btn" disabled={busy || !stores.length}>新建并打开</button>
          </form>
        </aside>

        <section className="panel list-panel">
          <div className="panel-title"><h3>消息列表</h3><span>{filtered.length}</span></div>
          <div className="conversation-list-scroll">
            {filtered.map(c => {
              const s = c.store_id ? storeMap.get(c.store_id) : undefined;
              return <button key={c.id} className={`conversation-card v2 ${active?.id === c.id ? "selected" : ""}`} onClick={() => openConversation(c)}>
                <div className="card-top"><span className="risk-emoji">{riskIcon(c.risk_level)}</span><strong>{c.category || "未分类"}</strong><em>{s?.store_code || "-"}</em></div>
                <p>{c.subject || "Amazon 买家消息"}</p>
                <div className="card-meta"><span className={`risk-badge ${c.risk_level}`}>风险{riskText(c.risk_level)}</span><span>{statusLabel[c.status || "open"] || c.status}</span></div>
              </button>;
            })}
            {!filtered.length && <div className="empty-state small">当前筛选下暂无消息。</div>}
          </div>
        </section>

        <section className="panel chat-panel workspace-chat">
          <div className="panel-title">
            <div><h3>{active?.subject || "请选择一条消息"}</h3><p>{activeStore?.store_name || ""}</p></div>
            {active && <select className="select status-select" value={active.status || "open"} onChange={e => updateStatus(e.target.value)}>
              <option value="open">未处理</option><option value="processing">处理中</option><option value="waiting_customer">等待客户</option><option value="done">已完成</option><option value="closed">已关闭</option>
            </select>}
          </div>
          <div className="context-strip">
            <div><span>店铺</span><strong>{activeStore?.store_code || "-"}</strong></div>
            <div><span>分类</span><strong>{active?.category || "-"}</strong></div>
            <div><span>状态</span><strong>{active ? statusLabel[active.status || "open"] : "-"}</strong></div>
          </div>
          <div className="chat-scroll">
            {messages.map(m => <div key={m.id} className={`bubble ${m.sender_type}`}><small>{m.sender_type === "buyer" ? "买家" : "客服"}</small>{m.content}</div>)}
            {!active && <div className="empty-state">左侧新建或选择一条 Amazon 买家消息。</div>}
          </div>
          <div className="attachment-panel">
            <div className="attachment-header">
              <label>附件 / 客户图片</label>
              <label className={`upload-btn ${!active || uploading ? "disabled" : ""}`}>
                {uploading ? "上传中..." : "上传文件"}
                <input
                  type="file"
                  disabled={!active || uploading}
                  onChange={e => { const file = e.target.files?.[0]; if (file) uploadAttachment(file); e.currentTarget.value = ""; }}
                />
              </label>
            </div>
            <div className="attachment-list">
              {attachments.map(a => <div key={a.id} className="attachment-item">
                <span>📎 {a.file_name}</span>
                <small>{a.content_type || "file"} · {a.file_size ? `${Math.round(a.file_size / 1024)} KB` : "-"}</small>
              </div>)}
              {active && !attachments.length && <p className="muted attachment-empty">暂无附件。</p>}
            </div>
          </div>
          <div className="internal-note">
            <label>内部备注</label>
            <input className="input" value={internalNote} onChange={e => setInternalNote(e.target.value)} placeholder="例如：客户比较急，先人工确认后回复。" />
          </div>
        </section>

        <aside className="panel ai-panel">
          <div className="panel-title"><h3>AI 工作区</h3><span className="copilot-badge">Copilot</span></div>
          <div className="analysis-box v2">
            <div><span>分类</span><strong>{reply?.detected_category || active?.category || "-"}</strong></div>
            <div><span>Intent</span><strong>{reply?.detected_intent || "待生成"}</strong></div>
            <div><span>风险</span><strong>{reply?.risk_level || active?.risk_level || "-"}</strong></div>
            <div><span>置信度</span><strong>{reply?.confidence_score ? `${Number(reply.confidence_score).toFixed(0)}%` : "待生成"}</strong></div>
          </div>
          <div className="quick-actions">
            <button disabled={!active} onClick={() => generateReply("polite")}>标准礼貌</button>
            <button disabled={!active} onClick={() => generateReply("apology")}>加强道歉</button>
            <button disabled={!active} onClick={() => generateReply("short")}>简短回复</button>
          </div>
          <label>回复语气</label>
          <select className="select" value={tone} onChange={e => setTone(e.target.value)}>
            <option value="polite">标准礼貌</option>
            <option value="apology">加强道歉</option>
            <option value="short">简短回复</option>
          </select>
          <button className="btn full" disabled={!active || busy} onClick={() => generateReply()}>{busy ? "处理中..." : "生成 AI 日语回复"}</button>
          <div className="template-quick-box">
            <div className="template-quick-head"><strong>快捷模板</strong><span>{active?.category || "当前分类"}</span></div>
            {matchedTemplates.map(t => (
              <button key={t.id} disabled={!active} onClick={() => setFinalReply(t.content_ja)} title={t.content_zh || t.title}>
                {t.title}
              </button>
            ))}
            {active && !matchedTemplates.length && <p className="muted">当前分类暂无启用模板。</p>}
          </div>
          <label>AI 回复草稿（可编辑）</label>
          <textarea className="textarea reply-box" value={finalReply} onChange={e => setFinalReply(e.target.value)} placeholder="点击生成后，这里会出现日语回复草稿，也可以先套用快捷模板。" />
          <div className="action-row three">
            <button className="btn secondary" disabled={!reply || busy} onClick={() => generateReply()}>重新生成</button>
            <button className="btn secondary" disabled={!finalReply} onClick={copyReply}>复制</button>
            <button className="btn" disabled={!finalReply || busy} onClick={saveSellerReply}>标记完成</button>
          </div>
          <div className="timeline-box">
            <h4>AI 判断依据</h4>
            <p>分类：{reply?.detected_category || active?.category || "-"}</p>
            <p>意图：{reply?.detected_intent || "待生成"}</p>
            <p>说明：V1 使用可追溯规则模板，后续再接入知识库与订单物流。</p>
          </div>
          <div className="timeline-box">
            <h4>Timeline</h4>
            <p>① 买家消息进入</p>
            <p>② AI 生成回复草稿</p>
            <p>③ 人工复制到 Amazon 后台</p>
            <p>④ 标记完成并留档</p>
          </div>
          <div className="note-box">V1 先复制到 Amazon 后台回复；自动发送放到 Amazon API 阶段。</div>
        </aside>
      </div>
    </AppShell>
  );
}
