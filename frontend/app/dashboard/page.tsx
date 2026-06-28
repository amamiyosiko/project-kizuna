import AppShell from "@/components/AppShell";

const kpis = [
  ["今日消息", "126"],
  ["未处理", "18"],
  ["AI待确认", "7"],
  ["高风险", "3"]
];

export default function DashboardPage() {
  return (
    <AppShell>
      <h2>Dashboard 总览</h2>
      <div className="grid grid-4">
        {kpis.map(([label, value]) => <div className="card" key={label}><div>{label}</div><div className="kpi">{value}</div></div>)}
      </div>
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginTop: 16 }}>
        <div className="card">
          <h3>按店铺消息量</h3>
          <table><tbody>{["Amazon店A", "Amazon店B", "Amazon店C"].map((s, i) => <tr key={s}><td>{s}</td><td>{[32, 21, 14][i]}</td></tr>)}</tbody></table>
        </div>
        <div className="card">
          <h3>售后分类</h3>
          <table><tbody>{[["配送未到", 42], ["返品希望", 18], ["商品破损", 6], ["差评风险", 3]].map(([c, n]) => <tr key={c}><td>{c}</td><td>{n}</td></tr>)}</tbody></table>
        </div>
      </div>
    </AppShell>
  );
}
