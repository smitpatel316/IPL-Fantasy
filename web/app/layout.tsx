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
      <body className="flex min-h-screen flex-col bg-ink-950 text-zinc-100 antialiased">
        <Nav />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 pb-20 pt-6 sm:pt-8">
          {children}
        </main>
        <footer className="border-t hairline">
          <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-2 px-4 py-6 text-xs text-zinc-600 sm:flex-row">
            <p>
              <span className="font-semibold text-zinc-400">IPL Fantasy</span> · built for
              friends, scored like the pros
            </p>
            <p>Standard T20 fantasy points · IPL 2027</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
