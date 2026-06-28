import AppShell from "@/components/AppShell";

const items = [
  { title: "工作项中心", desc: "查看和处理 Amazon 买家售后问题", href: "/workspace", icon: "🎫" },
  { title: "店铺管理", desc: "维护 Amazon JP 店铺信息", href: "/stores", icon: "🏪" },
  { title: "Amazon 接入", desc: "SP-API 准备状态与手动导入", href: "/amazon", icon: "🔌" },
  { title: "回复模板", desc: "管理常用日语客服回复", href: "/templates", icon: "💬" },
  { title: "知识库", desc: "维护 AI 回复依据和售后规则", href: "/knowledge", icon: "📚" },
];

export default function DashboardPage() {
  return (
    <AppShell>
      <div className="page-header">
        <div>
          <h2>首页</h2>
          <p>Project Kizuna 已进入生产使用阶段。请从工作项中心开始处理客服消息。</p>
        </div>
        <div className="summary-pill">Project Kizuna v0.3.4.1</div>
      </div>

      <div className="grid grid-4">
        <div className="card status-card"><span>API</span><strong>正常</strong></div>
        <div className="card status-card"><span>数据库</span><strong>正常</strong></div>
        <div className="card status-card"><span>S3</span><strong>已接通</strong></div>
        <div className="card status-card"><span>AI</span><strong>回复助手</strong></div>
      </div>

      <div className="module-grid">
        {items.map(item => (
          <a className="module-card" href={item.href} key={item.href}>
            <span>{item.icon}</span>
            <strong>{item.title}</strong>
            <p>{item.desc}</p>
          </a>
        ))}
      </div>
    </AppShell>
  );
}
