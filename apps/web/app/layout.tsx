import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./studio.css";

export const metadata: Metadata = {
  title: "Affiliate Studio",
  description: "จัดการสินค้าและตรวจตัวอย่าง Reel ในพื้นที่ทำงาน",
};

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="th">
      <body>{children}</body>
    </html>
  );
}
