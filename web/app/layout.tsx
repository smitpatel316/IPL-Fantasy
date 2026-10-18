import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import { LeagueProvider } from "@/lib/league-context";
import { ThemeProvider } from "@/lib/theme";
import { THEME_STORAGE_KEY } from "@/lib/theme-key";

export const metadata: Metadata = {
  title: "IPL Fantasy — Season-Long Fantasy Cricket",
  description:
    "Yahoo-style season-long IPL fantasy: snake draft, weekly head-to-head, FAAB waivers, trades, playoffs.",
};

/** Runs before first paint: applies the stored theme, else
 *  prefers-color-scheme, defaulting to dark (the original look). */
const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");if(t!=="light"&&t!=="dark"){t=window.matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";}document.documentElement.setAttribute("data-theme",t);}catch(e){document.documentElement.setAttribute("data-theme","dark");}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="flex min-h-screen flex-col bg-ink-950 text-zinc-100 antialiased">
        <ThemeProvider>
          <LeagueProvider>
            <Nav />
            <main className="mx-auto w-full max-w-6xl flex-1 px-4 pb-20 pt-6 sm:pt-8">
              {children}
            </main>
          </LeagueProvider>
        </ThemeProvider>
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
