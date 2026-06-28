import AppShell from "@/components/AppShell";

export default function AICenterPage() {
  return (
    <AppShell>
      <div className="page-header">
        <div>
          <h2>AI助手</h2>
          <p>这里后续用于管理 AI 摘要、AI 分类、AI 回复和模型配置。买家回复仍保持日语输出。</p>
        </div>
        <div className="summary-pill">规划中</div>
      </div>
      <div className="card empty-module">
        <h3>AI能力将在后续版本逐步上线</h3>
        <p>当前请先在工单中心处理消息。配置 OpenAI API Key 后，将支持自动生成日语回复草稿。</p>
      </div>
    </AppShell>
  );
}
