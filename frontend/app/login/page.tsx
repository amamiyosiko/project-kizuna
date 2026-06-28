"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, setTokens } from "@/lib/api";

type LoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  must_change_password: boolean;
};

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password })
      });
      setTokens(data.access_token, data.refresh_token);
      router.push(data.must_change_password ? "/profile" : "/workspace");
    } catch (err) {
      setError("登录失败：请确认账号密码，或后端服务是否已启动。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={submit}>
        <div className="brand-mark">絆</div>
        <h1>Project Kizuna</h1>
        <p>Amazon JP AI 客服工作台</p>
        <label>账号</label>
        <input className="input" value={username} onChange={e => setUsername(e.target.value)} placeholder="用户名" autoComplete="username" />
        <label>密码</label>
        <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="密码" autoComplete="current-password" />
        {error && <div className="error-box">{error}</div>}
        <button className="btn login-btn" disabled={loading}>{loading ? "登录中..." : "登录"}</button>
      </form>
    </main>
  );
}
