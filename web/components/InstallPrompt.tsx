"use client";

import { useCallback, useEffect, useState } from "react";
import { Download, X } from "lucide-react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

/** Shows an "Install app" banner on the home page once the browser fires
 *  beforeinstallprompt (i.e. the app is installable: manifest + SW).
 *  Dismissed state is remembered per browser. */
export default function InstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    try {
      if (localStorage.getItem("ipl-fantasy-install-dismissed") === "1") {
        setDismissed(true);
      }
    } catch {
      /* private mode — show anyway */
    }
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  const install = useCallback(async () => {
    if (!deferred) return;
    await deferred.prompt();
    await deferred.userChoice;
    setDeferred(null);
  }, [deferred]);

  const dismiss = useCallback(() => {
    try {
      localStorage.setItem("ipl-fantasy-install-dismissed", "1");
    } catch {
      /* ignore */
    }
    setDismissed(true);
    setDeferred(null);
  }, []);

  if (dismissed || !deferred) return null;

  return (
    <div className="mb-6 flex items-center gap-3 rounded-xl border hairline bg-ink-850 px-4 py-3">
      <Download className="h-5 w-5 shrink-0 text-gold-400" aria-hidden />
      <p className="flex-1 text-sm text-zinc-300">
        <span className="font-semibold text-zinc-100">Install IPL Fantasy</span> — add it to
        your home screen for draft-day access, even offline.
      </p>
      <button
        type="button"
        onClick={install}
        className="shrink-0 rounded-lg bg-gold-500 px-3 py-1.5 text-sm font-semibold text-on-gold hover:bg-gold-400"
      >
        Install
      </button>
      <button
        type="button"
        onClick={dismiss}
        aria-label="Dismiss install prompt"
        className="shrink-0 rounded-lg p-1.5 text-zinc-500 hover:text-zinc-200"
      >
        <X className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );
}
