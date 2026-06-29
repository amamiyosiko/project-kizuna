"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { apiFetch, clearTokens } from "@/lib/api";
import type { UserProfile } from "@/types";

type NavItem = {
  href: string;
  label: string;
  icon: string;
  anyOf?: string[];
};

const navItems: NavItem[] = [
  { href: "/dashboard", label: "首页", icon: "🏠" },
  { href: "/workspace", label: "工作项", icon: "🎫", anyOf: ["workitem.view"] },
  { href: "/ai-center", label: "AI助手", icon: "🧠", anyOf: ["ai.use", "config.manage"] },
  { href: "/knowledge", label: "知识库", icon: "📚", anyOf: ["workitem.view"] },
  { href: "/customers", label: "客户", icon: "👥", anyOf: ["workitem.view"] },
  { href: "/stores", label: "店铺", icon: "🏪", anyOf: ["store.manage"] },
  { href: "/amazon", label: "Amazon接入", icon: "🔌", anyOf: ["amazon.sync", "amazon.config.manage", "config.manage"] },
  { href: "/templates", label: "回复模板", icon: "💬", anyOf: ["workitem.reply", "ai.use"] },
  { href: "/settings", label: "系统设置", icon: "⚙️", anyOf: ["user.manage", "role.manage", "config.manage", "config.secret.manage", "audit.view"] },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [profile, setProfile] = useState<UserProfile | null>(null);

  useEffect(() => {
    apiFetch<UserProfile>("/auth/me")
      .then(setProfile)
      .catch(() => setProfile(null));
  }, []);

  const visibleNav = useMemo(() => {
    const permissions = new Set(profile?.permissions || []);
    return navItems.filter(item => !item.anyOf || item.anyOf.some(code => permissions.has(code)));
  }, [profile]);

  function logout() {
    clearTokens();
    router.push("/login");
  }

  return (
    <div className="admin-layout">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <div className="brand-mark small">絆</div>
          <div>
            <strong>Project Kizuna</strong>
            <span>AI客服运营平台</span>
          </div>
        </div>

        <nav className="admin-nav">
          {visibleNav.map(item => {
            const active = pathname === item.href || (item.href === "/workspace" && pathname.startsWith("/workspace")) || (item.href === "/settings" && pathname.startsWith("/settings"));
            return (
              <Link key={item.href} href={item.href} className={active ? "active" : ""}>
                <span>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="admin-sidebar-footer">
          <span>{profile?.role_name || "生产环境"}</span>
          <strong>v0.3.8</strong>
        </div>
      </aside>

      <div className="admin-main-shell">
        <header className="admin-header">
          <div className="header-search">
            <span>🔍</span>
            <input placeholder="搜索工作项 / 订单号 / 买家 / SKU" />
          </div>
          <div className="header-actions">
            <span className="system-status">● 系统正常</span>
            {profile && <span className="user-role-pill">{profile.username} · {profile.role_name || profile.role}</span>}
            <button className="btn secondary" onClick={logout}>退出登录</button>
          </div>
        </header>
        <main className="admin-content">{children}</main>
      </div>
    </div>
  );
}
