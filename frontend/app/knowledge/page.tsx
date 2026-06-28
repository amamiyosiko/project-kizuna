import AppShell from "@/components/AppShell";

export default function KnowledgePage() {
  return (
    <AppShell>
      <h2>知识库</h2>
      <div className="card">
        <p>V1 知识库用于维护 AI 回复依据，例如破损处理、返品规则、配送延迟话术。</p>
        <div className="grid">
          <input className="input" placeholder="规则标题" />
          <select className="select"><option>配送未到</option><option>商品破损</option><option>返品希望</option></select>
          <textarea className="textarea" placeholder="规则内容：AI生成回复时必须遵守的售后政策" />
          <button className="btn" style={{ width: 120 }}>保存规则</button>
        </div>
      </div>
    </AppShell>
  );
}
