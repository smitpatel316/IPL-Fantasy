import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "IPL Fantasy — Season-Long Fantasy Cricket",
  description:
    "Yahoo-style season-long IPL fantasy: snake draft, weekly head-to-head, FAAB waivers, trades, playoffs.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-midnight text-slate-100 antialiased">
        <Nav />
        <main className="mx-auto w-full max-w-6xl px-4 pb-16 pt-6">{children}</main>
      </body>
    </html>
  );
}
