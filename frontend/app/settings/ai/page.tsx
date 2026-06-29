"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import type { ConfigItem, UserProfile } from "@/types";

const aiKeys = ["AI_PROVIDER", "OPENAI_API_KEY", "OPENAI_MODEL", "GEMINI_API_KEY", "GEMINI_MODEL"];
const placeholders: Record<string, string> = {
  AI_PROVIDER: "openai / gemini / auto / rule",
  OPENAI_API_KEY: "sk-proj-...",
  OPENAI_MODEL: "gpt-4.1-mini",
  GEMINI_API_KEY: "Gemini API Key，可先留空",
  GEMINI_MODEL: "gemini-2.5-flash",
};

export default function AISettingsPage() {
  const router = useRouter();
  const [me, setMe] = useState<UserProfile | null>(null);
  const [configs, setConfigs] = useState<ConfigItem[]>([]);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const items = useMemo(() => configs.filter(c => aiKeys.includes(c.key)), [configs]);
  const canSecret = Boolean(me?.permissions?.includes("config.secret.manage"));

  async function load() {
    try {
      const profile = await apiFetch<UserProfile>("/auth/me");
      setMe(profile);
      if (!profile.permissions?.includes("config.manage")) {
        setError("当前账号没有配置管理权限。");
        return;
      }
      setConfigs(await apiFetch<ConfigItem[]>("/admin/configs"));
    } catch {
      router.push("/login");
    }
  }

  useEffect(() => { load(); }, []);

  async function save(item: ConfigItem) {
    const value = (draft[item.key] || "").trim();
    if (!value) {
      setError("请输入配置值。密钥不会回显，保存时需要重新粘贴完整值。");
      return;
    }
    setLoading(true);
    setNotice("");
    setError("");
    try {
      const updated = await apiFetch<ConfigItem>(`/admin/configs/${item.key}`, {
        method: "PUT",
        body: JSON.stringify({ key: item.key, value }),
      });
      setConfigs(current => current.map(c => c.key === item.key ? updated : c));
      setDraft(current => ({ ...current, [item.key]: "" }));
      setNotice(`${item.label} 已保存。`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <div className="page-header">
        <div>
          <h2>AI 配置</h2>
          <p>单独管理 GPT / Gemini / 默认 Provider。敏感 Key 只允许超级管理员维护，页面不会回显完整密钥。</p>
        </div>
        <button className="btn secondary" onClick={() => router.push("/settings")}>返回系统设置</button>
      </div>

      {notice && <div className="error-box neutral">{notice}</div>}
      {error && <div className="error-box">{error}</div>}

      <section className="card settings-panel-wide">
        <div className="panel-title"><h3>AI 模型配置</h3><span>v0.3.8</span></div>
        <div className="config-grid">
          {items.map(item => (
            <div className="config-item" key={item.key}>
              <div>
                <strong>{item.label}</strong>
                <span>{item.key} · {item.source}</span>
                <em className={item.configured ? "ok" : "warn"}>{item.configured ? `已配置：${item.value}` : "未配置"}</em>
              </div>
              <div className="config-edit-row">
                <input className="input" type={item.is_secret ? "password" : "text"} placeholder={item.is_secret ? "粘贴完整密钥保存，页面不会回显" : placeholders[item.key] || "配置值"} value={draft[item.key] || ""} onChange={e => setDraft({ ...draft, [item.key]: e.target.value })} />
                <button className="btn secondary" onClick={() => save(item)} disabled={loading || (item.is_secret && !canSecret)}>保存</button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
