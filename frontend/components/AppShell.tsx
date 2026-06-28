"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearTokens } from "@/lib/api";

const navItems = [
  { href: "/dashboard", label: "首页", icon: "🏠" },
  { href: "/workspace", label: "工作项", icon: "🎫" },
  { href: "/ai-center", label: "AI助手", icon: "🧠" },
  { href: "/knowledge", label: "知识库", icon: "📚" },
  { href: "/customers", label: "客户", icon: "👥" },
  { href: "/stores", label: "店铺", icon: "🏪" },
  { href: "/templates", label: "回复模板", icon: "💬" },
  { href: "/settings", label: "系统设置", icon: "⚙️" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

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
          {navItems.map(item => {
            const active = pathname === item.href || (item.href === "/workspace" && pathname.startsWith("/workspace"));
            return (
              <Link key={item.href} href={item.href} className={active ? "active" : ""}>
                <span>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="admin-sidebar-footer">
          <span>生产环境</span>
          <strong>v0.3.1</strong>
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
            <button className="btn secondary" onClick={logout}>退出登录</button>
          </div>
        </header>
        <main className="admin-content">{children}</main>
      </div>
    </div>
  );
}
