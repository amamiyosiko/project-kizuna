import "./globals.css";

export const metadata = {
  title: "Project Kizuna",
  description: "Amazon JP AI 客服运营平台"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
