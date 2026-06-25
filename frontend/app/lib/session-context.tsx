"use client";

import React, { createContext, useContext, useState } from "react";
import type { Lang } from "./i18n";

// Minimal cross-page shared state. The heavy lifting (analysis, chat, file
// upload, all the result state) stays inside DashboardShell; this only holds
// what the persistent Nav needs across route changes: whether a session
// exists (to enable the chat button) and the selected UI language.
type SessionCtx = {
  sessionId: string | null;
  setSessionId: (v: string | null) => void;
  lang: Lang;
  setLang: (v: Lang) => void;
};

const Ctx = createContext<SessionCtx | null>(null);

export function useSession(): SessionCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useSession must be used within <SessionProvider>");
  return c;
}

export const RESULT_STORE_KEY = "taxcalamity.result";

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [lang, setLang] = useState<Lang>("th");
  return (
    <Ctx.Provider value={{ sessionId, setSessionId, lang, setLang }}>
      {children}
    </Ctx.Provider>
  );
}
