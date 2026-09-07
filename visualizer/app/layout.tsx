import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CourtScope · 羽毛球视觉–IMU研究工具",
  description: "探索 BadmintonFusion35 的公开安全试次、动作级汇总和机器审计统计证据。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
