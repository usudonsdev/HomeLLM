import type { ReactNode } from "react";
import Link from "next/link";
import { Syne, Manrope } from "next/font/google";
import "./globals.css";

const display = Syne({ subsets: ["latin"], variable: "--font-display" });
const body = Manrope({ subsets: ["latin"], variable: "--font-body" });

export const metadata = {
  title: "HomeLLM",
  description: "Local job-hunting drawer and Valorant video pipeline console",
};

const nav = [
  { href: "/", label: "Status" },
  { href: "/experiences/", label: "Experiences" },
  { href: "/rag/", label: "RAG" },
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
            Pi hosts UI only. APIs and media stay on the Windows compute node.
          </footer>
        </div>
      </body>
    </html>
  );
}
