import AppShell from "@/components/AppShell";

export default function CustomersPage() {
  return (
    <AppShell>
      <div className="page-header">
        <div>
          <h2>客户</h2>
          <p>客户资料会随着 Amazon 消息同步和工单处理逐步沉淀。</p>
        </div>
        <div className="summary-pill">待接入 Amazon</div>
      </div>
      <div className="card empty-module">
        <h3>暂无客户资料</h3>
        <p>后续 Amazon 消息接入后，系统会自动根据 Buyer 信息建立客户记录。</p>
      </div>
    </AppShell>
  );
}
