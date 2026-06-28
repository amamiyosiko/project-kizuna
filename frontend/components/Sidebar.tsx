import Link from "next/link";

const items = [
  ["/dashboard", "Dashboard"],
  ["/messages", "客服中心"],
  ["/stores", "店铺管理"],
  ["/templates", "回复模板"],
  ["/knowledge", "知识库"],
  ["/settings", "系统设置"]
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <h1>ReplyFlow JP</h1>
      {items.map(([href, label]) => <Link key={href} href={href}>{label}</Link>)}
    </aside>
  );
}
