"use client";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import type { AIReply, Conversation, Message, Store } from "@/types";

const statuses = ["open", "pending", "replied", "follow_up", "closed", "exception"];
const categories = ["配送未到", "配送延迟", "商品破损", "商品不良", "缺件", "错发", "返品希望", "退款咨询", "使用方法", "差评风险", "其他"];

export default function MessagesPage() {
  const [stores, setStores] = useState<Store[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [reply, setReply] = useState<AIReply | null>(null);
  const [newMsg, setNewMsg] = useState("まだ届きません。");
  const [newConv, setNewConv] = useState({ store_id: 1, subject: "配送について", category: "配送未到", risk_level: "low" });

  async function load() {
    try {
      const [s, c] = await Promise.all([apiFetch<Store[]>("/stores"), apiFetch<Conversation[]>("/conversations")]);
      setStores(s); setConversations(c);
      if (s[0]) setNewConv(v => ({ ...v, store_id: s[0].id }));
    } catch {}
  }
  useEffect(() => { load(); }, []);

  async function openConversation(c: Conversation) {
    setActive(c); setReply(null);
    try { setMessages(await apiFetch<Message[]>(`/conversations/${c.id}/messages`)); } catch { setMessages([]); }
  }

  async function createConversation(e: React.FormEvent) {
    e.preventDefault();
    const c = await apiFetch<Conversation>("/conversations", { method: "POST", body: JSON.stringify(newConv) });
    await apiFetch<Message>(`/conversations/${c.id}/messages`, { method: "POST", body: JSON.stringify({ sender_type: "buyer", content: newMsg }) });
    await load();
    await openConversation(c);
  }

  async function generateReply() {
    if (!active) return;
    const r = await apiFetch<AIReply>("/ai/generate-reply", { method: "POST", body: JSON.stringify({ conversation_id: active.id }) });
    setReply(r);
  }

  async function approveReply() {
    if (!reply) return;
    const text = (document.getElementById("finalReply") as HTMLTextAreaElement)?.value || reply.ai_reply_text;
    const r = await apiFetch<AIReply>(`/ai/approve-reply/${reply.id}`, { method: "POST", body: JSON.stringify({ final_reply_text: text }) });
    setReply(r);
    await navigator.clipboard?.writeText(r.final_reply_text || r.ai_reply_text);
  }

  return (
    <AppShell>
      <div className="three-pane">
        <section className="card">
          <h3>筛选</h3>
          <label>店铺</label>
          <select className="select"><option>全部店铺</option>{stores.map(s => <option key={s.id}>{s.store_name}</option>)}</select>
          <label>状态</label>
          <select className="select">{statuses.map(s => <option key={s}>{s}</option>)}</select>
          <label>分类</label>
          <select className="select">{categories.map(c => <option key={c}>{c}</option>)}</select>
          <hr />
          <h3>录入新消息</h3>
          <form className="grid" onSubmit={createConversation}>
            <select className="select" value={newConv.store_id} onChange={e => setNewConv({ ...newConv, store_id: Number(e.target.value) })}>{stores.map(s => <option value={s.id} key={s.id}>{s.store_name}</option>)}</select>
            <input className="input" value={newConv.subject} onChange={e => setNewConv({ ...newConv, subject: e.target.value })} placeholder="主题" />
            <select className="select" value={newConv.category} onChange={e => setNewConv({ ...newConv, category: e.target.value })}>{categories.map(c => <option key={c}>{c}</option>)}</select>
            <textarea className="textarea" value={newMsg} onChange={e => setNewMsg(e.target.value)} placeholder="买家消息（日语）" />
            <button className="btn">创建会话</button>
          </form>
        </section>

        <section className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: 16, borderBottom: "1px solid #eef2f7" }}><h3 style={{ margin: 0 }}>消息列表</h3></div>
          {conversations.map(c => (
            <div key={c.id} className="list-item" onClick={() => openConversation(c)}>
              <strong>{c.subject || `Conversation #${c.id}`}</strong>
              <p style={{ margin: "6px 0", color: "#6b7280" }}>店铺ID：{c.store_id} · {c.category || "未分类"}</p>
              <span className="badge">{c.status}</span> <span className="badge">{c.risk_level}</span>
            </div>
          ))}
        </section>

        <section className="card">
          <h3>消息详情</h3>
          {!active ? <p>请选择或创建一个会话。</p> : <>
            <p><strong>主题：</strong>{active.subject}</p>
            <p><strong>分类：</strong>{active.category} <span className="badge">{active.risk_level}</span></p>
            <h4>对话内容</h4>
            {messages.map(m => <div key={m.id} className="card" style={{ marginBottom: 8 }}><strong>{m.sender_type}</strong><p>{m.content}</p></div>)}
            <button className="btn" onClick={generateReply}>生成AI回复</button>
            {reply && <div style={{ marginTop: 16 }}>
              <h4>AI识别结果</h4>
              <p>分类：{reply.detected_category} · 风险：{reply.risk_level} · 置信度：{reply.confidence_score}</p>
              <h4>AI回复草稿</h4>
              <textarea id="finalReply" className="textarea" defaultValue={reply.final_reply_text || reply.ai_reply_text} />
              <div style={{ marginTop: 12 }}>
                <button className="btn" onClick={approveReply}>确认并复制</button>
              </div>
            </div>}
          </>}
        </section>
      </div>
    </AppShell>
  );
}
