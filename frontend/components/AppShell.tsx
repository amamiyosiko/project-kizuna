"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearTokens } from "@/lib/api";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  function logout() {
    clearTokens();
    router.push("/login");
  }
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-brand"><span>絆</span> Project Kizuna</div>
        <nav>
          <Link href="/workspace">Workspace</Link>
          <Link href="/stores">Stores</Link>
          <Link href="/templates">Templates</Link>
          <Link href="/settings">Settings</Link>
        </nav>
        <button className="btn secondary" onClick={logout}>退出</button>
      </header>
      <main className="app-main">{children}</main>
    </div>
  );
}
