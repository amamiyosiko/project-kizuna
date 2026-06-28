"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

type Me = { id: number; username: string; role: string; status: string; must_change_password: boolean };

export default function ProfilePage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    apiFetch<Me>("/auth/me").then(setMe).catch(() => router.push("/login"));
  }, [router]);

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    setMessage("");
    try {
      await apiFetch<Me>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
      });
      setMessage("密码已修改，正在进入工作台。");
      setTimeout(() => router.push("/workspace"), 800);
    } catch {
      setMessage("修改失败：请确认旧密码，新密码至少 8 位。");
    }
  }

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={changePassword}>
        <div className="brand-mark">絆</div>
        <h1>首次登录设置</h1>
        <p>当前用户：{me?.username || "加载中"} / {me?.role || ""}</p>
        <label>旧密码</label>
        <input className="input" type="password" value={oldPassword} onChange={e => setOldPassword(e.target.value)} />
        <label>新密码</label>
        <input className="input" type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} placeholder="至少 8 位" />
        {message && <div className="error-box neutral">{message}</div>}
        <button className="btn login-btn">保存并进入工作台</button>
        <button className="btn secondary" type="button" onClick={() => router.push("/workspace")}>稍后再改</button>
      </form>
    </main>
  );
}
