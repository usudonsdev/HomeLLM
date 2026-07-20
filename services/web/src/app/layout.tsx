import type { ReactNode } from "react";
import Link from "next/link";
import { Zen_Kaku_Gothic_New, Noto_Sans_JP } from "next/font/google";
import "./globals.css";

const display = Zen_Kaku_Gothic_New({
  weight: ["500", "700"],
  subsets: ["latin"],
  variable: "--font-display",
});
const body = Noto_Sans_JP({
  weight: ["400", "500", "700"],
  subsets: ["latin"],
  variable: "--font-body",
});

export const metadata = {
  title: "HomeLLM",
  description: "完全ローカルの就活引き出しと動画解析コンソール",
};

const nav = [
  { href: "/", label: "状態" },
  { href: "/experiences/", label: "経験ログ" },
  { href: "/rag/", label: "引き出し" },
  { href: "/videos/", label: "Valorant" },
];

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja" className={`${display.variable} ${body.variable}`}>
      <body>
        <div className="shell">
          <header className="top">
            <Link href="/" className="brand">
              HomeLLM
            </Link>
            <nav className="nav">
              {nav.map((item) => (
                <Link key={item.href} href={item.href}>
                  {item.label}
                </Link>
              ))}
            </nav>
          </header>
          <main className="main">{children}</main>
          <footer className="foot">
            Web は Raspberry Pi。API・DB・Ollama・動画処理は Windows 側で動かします。
          </footer>
        </div>
      </body>
    </html>
  );
}
