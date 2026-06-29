"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import type { ConfigItem, UserProfile } from "@/types";

const amazonGlobalKeys = ["AMAZON_LWA_CLIENT_ID", "AMAZON_LWA_CLIENT_SECRET", "AMAZON_MARKETPLACE_ID", "AMAZON_REGION"];
const placeholders: Record<string, string> = {
  AMAZON_LWA_CLIENT_ID: "Amazon LWA Client ID",
  AMAZON_LWA_CLIENT_SECRET: "Amazon LWA Client Secret",
  AMAZON_MARKETPLACE_ID: "A1VC38T7YXB528",
  AMAZON_REGION: "jp",
};

export default function AmazonSettingsPage() {
  const router = useRouter();
  const [me, setMe] = useState<UserProfile | null>(null);
  const [configs, setConfigs] = useState<ConfigItem[]>([]);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const items = useMemo(() => configs.filter(c => amazonGlobalKeys.includes(c.key)), [configs]);
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
          <h2>Amazon 全局配置</h2>
          <p>这里管理 Amazon SP-API 应用级配置；每家店铺的 Seller ID、Refresh Token 和同步开关请到【店铺管理】维护。</p>
        </div>
        <div className="button-row">
          <button className="btn secondary" onClick={() => router.push("/stores")}>去店铺授权</button>
          <button className="btn secondary" onClick={() => router.push("/settings")}>返回系统设置</button>
        </div>
      </div>

      {notice && <div className="error-box neutral">{notice}</div>}
      {error && <div className="error-box">{error}</div>}

      <section className="card settings-panel-wide">
        <div className="panel-title"><h3>Amazon SP-API 应用配置</h3><span>Global</span></div>
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

      <section className="card settings-panel-wide">
        <div className="panel-title"><h3>多店铺授权说明</h3><span>Store</span></div>
        <div className="permission-hint-grid">
          <div className="permission-hint-card"><strong>应用级配置</strong><p>Client ID、Client Secret、默认 Marketplace、Region 统一维护。</p></div>
          <div className="permission-hint-card"><strong>店铺级配置</strong><p>每家店铺单独维护 Seller ID、Refresh Token、同步开关，支持 JP01、JP02 等多店铺。</p></div>
          <div className="permission-hint-card"><strong>日常同步</strong><p>/amazon 页面只做连接测试、订单同步、同步记录查看，不再堆放密钥输入。</p></div>
        </div>
      </section>
    </AppShell>
  );
}
