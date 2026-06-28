import AppShell from "@/components/AppShell";

export default function SettingsPage() {
  return (
    <AppShell>
      <h2>系统设置</h2>
      <div className="card grid">
        <label>OpenAI Model</label>
        <input className="input" defaultValue="gpt-4.1-mini" />
        <label>AI默认回复语言</label>
        <select className="select"><option>日本語</option><option>中文</option></select>
        <label>高风险消息是否必须人工审核</label>
        <select className="select"><option>是</option><option>否</option></select>
        <button className="btn" style={{ width: 120 }}>保存设置</button>
      </div>
    </AppShell>
  );
}
