"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import type { AdminUser, AuditLog, ConfigItem, Permission, Role, UserProfile } from "@/types";

type UserForm = {
  username: string;
  password: string;
  full_name: string;
  email: string;
  role_code: string;
};

type ConfigDraft = Record<string, string>;

const defaultUserForm: UserForm = {
  username: "",
  password: "",
  full_name: "",
  email: "",
  role_code: "agent",
};

const configPlaceholders: Record<string, string> = {
  AI_PROVIDER: "openai / gemini / auto / rule",
  OPENAI_API_KEY: "sk-proj-...",
  OPENAI_MODEL: "gpt-4.1-mini",
  GEMINI_API_KEY: "Gemini API Key，可先留空",
  GEMINI_MODEL: "gemini-2.5-flash",
  AMAZON_LWA_CLIENT_ID: "Amazon LWA Client ID",
  AMAZON_LWA_CLIENT_SECRET: "Amazon LWA Client Secret",
  AMAZON_REFRESH_TOKEN: "Amazon Refresh Token",
  AMAZON_MARKETPLACE_ID: "A1VC38T7YXB528",
  AMAZON_REGION: "jp",
};

export default function SettingsPage() {
  const router = useRouter();
  const [me, setMe] = useState<UserProfile | null>(null);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [configs, setConfigs] = useState<ConfigItem[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [configDraft, setConfigDraft] = useState<ConfigDraft>({});
  const [userForm, setUserForm] = useState<UserForm>(defaultUserForm);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [selectedRolePermissions, setSelectedRolePermissions] = useState<string[]>([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const can = (code: string) => Boolean(me?.permissions?.includes(code));

  const selectedRole = useMemo(() => roles.find(r => r.id === selectedRoleId) || null, [roles, selectedRoleId]);

  const permissionGroups = useMemo(() => {
    const grouped: Record<string, Permission[]> = {};
    permissions.forEach(permission => {
      const group = permission.group || "general";
      if (!grouped[group]) grouped[group] = [];
      grouped[group].push(permission);
    });
    return grouped;
  }, [permissions]);

  async function load() {
    try {
      const profile = await apiFetch<UserProfile>("/auth/me");
      setMe(profile);
      if (profile.permissions?.includes("role.manage")) {
        const [permissionList, roleList] = await Promise.all([
          apiFetch<Permission[]>("/admin/permissions"),
          apiFetch<Role[]>("/admin/roles"),
        ]);
        setPermissions(permissionList);
        setRoles(roleList);
        if (!selectedRoleId && roleList.length) {
          setSelectedRoleId(roleList[0].id);
          setSelectedRolePermissions(roleList[0].permissions || []);
        }
      }
      if (profile.permissions?.includes("user.manage")) {
        setUsers(await apiFetch<AdminUser[]>("/admin/users"));
      }
      if (profile.permissions?.includes("config.manage")) {
        setConfigs(await apiFetch<ConfigItem[]>("/admin/configs"));
      }
      if (profile.permissions?.includes("audit.view")) {
        setLogs(await apiFetch<AuditLog[]>("/admin/audit-logs"));
      }
    } catch {
      router.push("/login");
    }
  }

  useEffect(() => { load(); }, []);

  function chooseRole(role: Role) {
    setSelectedRoleId(role.id);
    setSelectedRolePermissions(role.permissions || []);
    setNotice(`正在编辑角色：${role.name}`);
    setError("");
  }

  async function saveRolePermissions() {
    if (!selectedRole) return;
    setLoading(true);
    setNotice("");
    setError("");
    try {
      await apiFetch<Role>(`/admin/roles/${selectedRole.id}`, {
        method: "PUT",
        body: JSON.stringify({ permission_codes: selectedRolePermissions }),
      });
      setNotice("角色权限已保存。");
      await load();
    } catch (err) {
      setError("保存角色权限失败。超级管理员权限固定，不能修改。 ");
    } finally {
      setLoading(false);
    }
  }

  async function createUser(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setNotice("");
    setError("");
    try {
      await apiFetch<AdminUser>("/admin/users", {
        method: "POST",
        body: JSON.stringify({ ...userForm, must_change_password: true, status: "active" }),
      });
      setUserForm(defaultUserForm);
      setNotice("账号已创建，首次登录需要修改密码。");
      await load();
    } catch {
      setError("创建账号失败：用户名可能重复，或密码少于 8 位。 ");
    } finally {
      setLoading(false);
    }
  }

  async function updateUserRole(user: AdminUser, roleCode: string) {
    await apiFetch<AdminUser>(`/admin/users/${user.id}`, { method: "PUT", body: JSON.stringify({ role_code: roleCode }) });
    await load();
  }

  async function toggleUserStatus(user: AdminUser) {
    await apiFetch<AdminUser>(`/admin/users/${user.id}`, {
      method: "PUT",
      body: JSON.stringify({ status: user.status === "active" ? "disabled" : "active" }),
    });
    await load();
  }

  async function resetUserPassword(user: AdminUser) {
    const password = window.prompt(`请输入 ${user.username} 的新临时密码，至少 8 位：`);
    if (!password) return;
    await apiFetch<AdminUser>(`/admin/users/${user.id}`, {
      method: "PUT",
      body: JSON.stringify({ password, must_change_password: true }),
    });
    setNotice("临时密码已设置，该账号下次登录需要修改密码。");
  }

  async function saveConfig(item: ConfigItem) {
    const value = (configDraft[item.key] ?? "").trim();
    if (!value) {
      setError("请输入新的配置值。密钥不会回显，保存时需要重新粘贴完整值。 ");
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
      setConfigDraft(current => ({ ...current, [item.key]: "" }));
      setNotice(`${item.label} 已保存。`);
    } catch {
      setError("保存配置失败：当前账号可能没有密钥管理权限。 ");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <div className="page-header">
        <div>
          <h2>系统设置</h2>
          <p>v0.3.8 细化权限控制、配置中心和正式接入流程。</p>
        </div>
        <div className="summary-pill">当前角色：{me?.role_name || me?.role || "-"}</div>
      </div>

      {notice && <div className="error-box neutral">{notice}</div>}
      {error && <div className="error-box">{error}</div>}

      <div className="settings-grid-v035">
        <section className="card settings-panel-wide">
          <div className="panel-title"><h3>账号与角色</h3><span>RBAC</span></div>
          {!can("user.manage") && <p className="muted">当前账号没有用户管理权限。</p>}
          {can("user.manage") && (
            <>
              <form className="user-create-row" onSubmit={createUser}>
                <input className="input" placeholder="用户名" value={userForm.username} onChange={e => setUserForm({ ...userForm, username: e.target.value })} required />
                <input className="input" placeholder="姓名" value={userForm.full_name} onChange={e => setUserForm({ ...userForm, full_name: e.target.value })} />
                <input className="input" placeholder="邮箱" value={userForm.email} onChange={e => setUserForm({ ...userForm, email: e.target.value })} />
                <input className="input" placeholder="临时密码，至少8位" type="password" value={userForm.password} onChange={e => setUserForm({ ...userForm, password: e.target.value })} required />
                <select className="select" value={userForm.role_code} onChange={e => setUserForm({ ...userForm, role_code: e.target.value })}>
                  {roles.map(role => <option key={role.code} value={role.code}>{role.name}</option>)}
                </select>
                <button className="btn" disabled={loading}>创建账号</button>
              </form>

              <table className="compact-table">
                <thead><tr><th>账号</th><th>姓名</th><th>角色</th><th>状态</th><th>操作</th></tr></thead>
                <tbody>
                  {users.map(user => (
                    <tr key={user.id}>
                      <td><strong>{user.username}</strong><br /><span className="muted">{user.email}</span></td>
                      <td>{user.full_name || "-"}</td>
                      <td>
                        <select className="select small-select" value={user.role || "agent"} onChange={e => updateUserRole(user, e.target.value)}>
                          {roles.map(role => <option key={role.code} value={role.code}>{role.name}</option>)}
                        </select>
                      </td>
                      <td><span className={`badge ${user.status === "active" ? "success" : "muted-badge"}`}>{user.status === "active" ? "启用" : "停用"}</span></td>
                      <td><button className="link-btn" onClick={() => resetUserPassword(user)}>重置密码</button><button className="link-btn" onClick={() => toggleUserStatus(user)}>{user.status === "active" ? "停用" : "启用"}</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </section>

        <section className="card settings-panel-wide">
          <div className="panel-title"><h3>角色权限</h3><span>Permission</span></div>
          {!can("role.manage") && <p className="muted">当前账号没有角色管理权限。</p>}
          {can("role.manage") && (
            <div className="role-permission-layout">
              <div className="role-list-box">
                {roles.map(role => <button key={role.id} className={selectedRoleId === role.id ? "active" : ""} onClick={() => chooseRole(role)}>{role.name}<span>{role.code}</span></button>)}
              </div>
              <div className="permission-list-box">
                <h4>{selectedRole?.name || "请选择角色"}</h4>
                <p className="muted">超级管理员权限固定；其他角色可按权限点控制页面和后端 API。</p>
                {Object.entries(permissionGroups).map(([group, items]) => (
                  <div className="permission-group" key={group}>
                    <strong>{group}</strong>
                    <div className="permission-checks">
                      {items.map(permission => (
                        <label key={permission.code}>
                          <input
                            type="checkbox"
                            checked={selectedRolePermissions.includes(permission.code)}
                            disabled={selectedRole?.code === "super_admin"}
                            onChange={e => {
                              setSelectedRolePermissions(current => e.target.checked ? [...current, permission.code] : current.filter(code => code !== permission.code));
                            }}
                          />
                          <span>{permission.name}</span><em>{permission.code}</em>
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
                <button className="btn" onClick={saveRolePermissions} disabled={loading || !selectedRole || selectedRole.code === "super_admin"}>保存角色权限</button>
              </div>
            </div>
          )}
        </section>

        <section className="card settings-panel-wide">
          <div className="panel-title"><h3>配置中心</h3><span>v0.3.8</span></div>
          {!can("config.manage") && <p className="muted">当前账号没有配置管理权限。</p>}
          {can("config.manage") && (
            <div className="permission-hint-grid">
              <div className="permission-hint-card">
                <strong>AI 配置</strong>
                <p>管理 OpenAI、Gemini、默认 Provider 和模型名称。</p>
                <button className="btn secondary" onClick={() => router.push("/settings/ai")}>进入 AI 配置</button>
              </div>
              <div className="permission-hint-card">
                <strong>Amazon 全局配置</strong>
                <p>管理 LWA Client ID、Client Secret、默认 Marketplace ID 和 Region。</p>
                <button className="btn secondary" onClick={() => router.push("/settings/amazon")}>进入 Amazon 配置</button>
              </div>
              <div className="permission-hint-card">
                <strong>多店铺授权</strong>
                <p>每家店铺单独维护 Seller ID、Refresh Token 和同步开关。</p>
                <button className="btn secondary" onClick={() => router.push("/stores")}>进入店铺管理</button>
              </div>
            </div>
          )}
        </section>

        <section className="card settings-panel-wide">
          <div className="panel-title"><h3>操作日志</h3><span>Audit</span></div>
          {!can("audit.view") && <p className="muted">当前账号没有日志查看权限。</p>}
          {can("audit.view") && (
            <table className="compact-table">
              <thead><tr><th>时间</th><th>动作</th><th>对象</th><th>详情</th></tr></thead>
              <tbody>
                {logs.map(log => <tr key={log.id}><td>{log.created_at?.slice(0, 19).replace("T", " ")}</td><td>{log.action}</td><td>{log.resource_type}:{log.resource_id}</td><td className="note-cell">{log.detail}</td></tr>)}
                {!logs.length && <tr><td colSpan={4} className="empty-table">暂无操作日志。</td></tr>}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </AppShell>
  );
}
