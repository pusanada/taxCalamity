"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, MessageCircle } from "lucide-react";
import { useSession } from "../lib/session-context";
import { LANGS, tr } from "../lib/i18n";

export function Nav() {
  const { sessionId, lang, setLang } = useSession();
  const pathname = usePathname();

  const tab = (href: string, label: string, active: boolean) => (
    <Link
      href={href}
      className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
        active
          ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
          : "text-slate-400 hover:text-slate-200 border border-transparent"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <header className="border-b border-white/5 bg-slate-950/60 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-2.5 bg-gradient-to-tr from-indigo-600 to-indigo-400 rounded-lg shadow-lg shadow-indigo-500/20 shrink-0">
            <Activity className="h-6 w-6 text-white" />
          </div>
          <div className="min-w-0">
            <h1 className="font-semibold text-lg tracking-tight truncate">{tr(lang, "appTitle")}</h1>
            <p className="text-xs text-slate-400 truncate">{tr(lang, "appSubtitle")}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          <nav className="hidden sm:flex items-center gap-1">
            {tab("/", tr(lang, "navIntake"), pathname === "/")}
            {tab("/results", tr(lang, "navResults"), pathname === "/results")}
          </nav>

          {/* Chat button — carries the session implicitly via shared context;
              disabled until an analysis has produced a session_id. */}
          {sessionId ? (
            <Link
              href="/chat"
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors ${
                pathname === "/chat"
                  ? "bg-indigo-500/25 text-indigo-200 border-indigo-500/40"
                  : "bg-indigo-500/10 text-indigo-300 border-indigo-500/20 hover:bg-indigo-500/20"
              }`}
            >
              <MessageCircle className="h-3.5 w-3.5" /> {tr(lang, "navChat")}
            </Link>
          ) : (
            <span
              title={tr(lang, "chatDisabledTip")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border border-white/5 text-slate-600 cursor-not-allowed"
            >
              <MessageCircle className="h-3.5 w-3.5" /> {tr(lang, "navChat")}
            </span>
          )}

          <span className="hidden md:inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            {tr(lang, "activeConnection")}
          </span>

          <select
            value={lang}
            onChange={(e) => setLang(e.target.value as any)}
            className="bg-slate-900/70 border border-white/10 rounded-md px-2 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500/40 cursor-pointer"
            aria-label="Language"
          >
            {LANGS.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </header>
  );
}
