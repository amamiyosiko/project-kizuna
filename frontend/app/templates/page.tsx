"use client";

import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import type { ReplyTemplate } from "@/types";

const categories = ["配送未到", "配送延迟", "商品破损", "商品不良", "缺件", "错发", "返品希望", "退款咨询", "使用方法", "差评风险", "其他"];
const risks = [
  { value: "low", label: "低风险" },
  { value: "medium", label: "中风险" },
  { value: "high", label: "高风险" },
];

const emptyForm = { category: "配送未到", title: "", content_ja: "", content_zh: "", risk_level: "low", is_active: true };

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<ReplyTemplate[]>([]);
  const [filter, setFilter] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setTemplates(await apiFetch<ReplyTemplate[]>("/templates"));
  }

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => templates.filter(t => !filter || t.category === filter), [templates, filter]);

  function edit(t: ReplyTemplate) {
    setEditingId(t.id);
    setForm({
      category: t.category || "配送未到",
      title: t.title,
      content_ja: t.content_ja,
      content_zh: t.content_zh || "",
      risk_level: t.risk_level || "low",
      is_active: t.is_active ?? true,
    });
  }

  function reset() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim() || !form.content_ja.trim()) return alert("请填写模板标题和日语内容");
    setBusy(true);
    try {
      if (editingId) {
        await apiFetch(`/templates/${editingId}`, { method: "PUT", body: JSON.stringify(form) });
      } else {
        await apiFetch("/templates", { method: "POST", body: JSON.stringify(form) });
      }
      reset();
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!confirm("确认删除这个回复模板吗？")) return;
    await apiFetch(`/templates/${id}`, { method: "DELETE" });
    await load();
  }

  async function toggle(t: ReplyTemplate) {
    await apiFetch(`/templates/${t.id}`, { method: "PUT", body: JSON.stringify({ is_active: !(t.is_active ?? true) }) });
    await load();
  }

  return (
    <AppShell>
      <div className="page-header"><div><h2>回复模板</h2><p>维护 Amazon JP 售后常用日语回复，Workspace 可一键套用。</p></div></div>
      <div className="grid two-col">
        <div className="card">
          <h3>{editingId ? "编辑模板" : "新增模板"}</h3>
          <form className="form-stack" onSubmit={submit}>
            <label>售后分类</label>
            <select className="select" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>{categories.map(c => <option key={c}>{c}</option>)}</select>
            <label>模板标题</label>
            <input className="input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="例如：破損写真依頼" />
            <label>风险等级</label>
            <select className="select" value={form.risk_level} onChange={e => setForm({ ...form, risk_level: e.target.value })}>{risks.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}</select>
            <label>日语回复内容</label>
            <textarea className="textarea template-textarea" value={form.content_ja} onChange={e => setForm({ ...form, content_ja: e.target.value })} placeholder="ご連絡ありがとうございます。" />
            <label>中文说明</label>
            <textarea className="textarea compact" value={form.content_zh} onChange={e => setForm({ ...form, content_zh: e.target.value })} placeholder="这个模板适用于什么场景" />
            <label className="check-row"><input type="checkbox" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} /> 启用模板</label>
            <div className="action-row">
              <button className="btn" disabled={busy}>{busy ? "保存中..." : editingId ? "保存修改" : "新增模板"}</button>
              {editingId && <button type="button" className="btn secondary" onClick={reset}>取消编辑</button>}
            </div>
          </form>
        </div>
        <div className="card">
          <div className="panel-title"><h3>模板列表</h3><select className="select small-select" value={filter} onChange={e => setFilter(e.target.value)}><option value="">全部分类</option>{categories.map(c => <option key={c}>{c}</option>)}</select></div>
          <div className="template-list">
            {filtered.map(t => <div className={`template-card ${t.is_active ? "" : "disabled"}`} key={t.id}>
              <div className="template-card-head"><strong>{t.title}</strong><span>{t.category}</span></div>
              <p>{t.content_ja}</p>
              {t.content_zh && <small>{t.content_zh}</small>}
              <div className="action-row template-actions">
                <button className="btn secondary" onClick={() => edit(t)}>编辑</button>
                <button className="btn secondary" onClick={() => toggle(t)}>{t.is_active ? "停用" : "启用"}</button>
                <button className="btn danger" onClick={() => remove(t.id)}>删除</button>
              </div>
            </div>)}
            {!filtered.length && <div className="empty-state small">暂无模板。</div>}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
