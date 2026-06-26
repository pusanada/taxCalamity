"use client";

import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  ShieldCheck, 
  ShieldAlert, 
  CheckCircle, 
  Info, 
  Clock, 
  FileText, 
  Activity, 
  RefreshCw,
  Coins,
  AlertTriangle,
  FileSpreadsheet,
  ChevronDown,
  Gauge,
  Send,
  Pencil,
  MessageCircle
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useSession, RESULT_STORE_KEY } from '../lib/session-context';
import { isSessionComplete } from '../lib/dashboard-data';
import { tr } from '../lib/i18n';
// Backend base URL. Set NEXT_PUBLIC_API_URL in the deployment environment
// (e.g. the Render backend URL); falls back to localhost for local dev.
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const PRESETS = [
  {
    name: "Client A (Salary, Compliant)",
    text: `อายุ 35 ปี\nเงินเดือนประมาณแสนห้า\nโบนัสปีละ 4 เดือน\nซื้อ RMF บ้างนิดหน่อย\nมีประกันชีวิตอยู่แล้ว\nอยากลดภาษีเพิ่ม\nความเสี่ยงปานกลาง เน้นพอร์ตแบบสมดุล`
  },
  {
    name: "Client B (Freelance, High-Tax)",
    text: `รายได้ไม่แน่นอน\nฟรีแลนซ์\nปีที่แล้วเสียภาษีเยอะมาก\nกำลังมองหา SSF\nความเสี่ยงสูง ชอบกองทุนเติบโต`
  },
  {
    name: "Client C (Conservative, Violating)",
    text: `ลูกค้าอายุ 55 ปี\nรายได้ 120,000 บาทต่อเดือน\nวัตถุประสงค์เพื่อลดหย่อนภาษี มีความเสี่ยงต่ำมาก\n*ต้องการรับประกันผลตอบแทนไม่ต่ำกว่า 15% เท่านั้น ห้ามขาดทุนเด็ดขาด*`
  },
  {
    name: "Client D (Low Confidence Test)",
    text: `อยากรวย`
  }
];

// Profile fields tracked for completeness + optional supplemental input.
// `penalty` is the confidence cost (%) charged when the field is missing.
const PROFILE_FIELDS: { key: string; label: string; penalty: number; placeholder: string; type: string }[] = [
  { key: "monthly_income", label: "Monthly Income (THB)", penalty: 10, placeholder: "e.g. 150000", type: "number" },
  { key: "age", label: "Age", penalty: 5, placeholder: "e.g. 35", type: "number" },
  { key: "risk_profile", label: "Risk Preference", penalty: 5, placeholder: "Conservative / Moderate / Aggressive", type: "text" },
  { key: "employment_type", label: "Employment Type", penalty: 5, placeholder: "salary / freelance", type: "text" },
  { key: "goal", label: "Financial Goal", penalty: 4, placeholder: "e.g. tax optimization", type: "text" },
  { key: "ssf", label: "SSF Investment (THB/year)", penalty: 3, placeholder: "e.g. 60000", type: "number" },
  { key: "rmf", label: "RMF Investment (THB/year)", penalty: 3, placeholder: "e.g. 30000", type: "number" },
  { key: "life_insurance", label: "Life Insurance (THB/year)", penalty: 3, placeholder: "e.g. 25000", type: "number" },
];

// Display helper: never surface null / undefined / NaN / empty — show a dash.
const dash = (v: any): string => {
  if (v === null || v === undefined) return "-";
  if (typeof v === "number" && Number.isNaN(v)) return "-";
  if (typeof v === "string" && v.trim() === "") return "-";
  return String(v);
};

// Map internal pipeline node ids (e.g. "node_6_explanation") to the
// human-readable agent name shown to clients, in the active language.
const AGENT_NAMES: Record<string, { th: string; en: string }> = {
  node_1_interpreter: { th: "ตัวแปลภาษาไทย (Typhoon)", en: "Thai Interpreter (Typhoon)" },
  node_2_intake: { th: "เจ้าหน้าที่รับข้อมูล", en: "Intake Agent" },
  node_3_suitability: { th: "นักวิเคราะห์ความเหมาะสม", en: "Suitability Analyst" },
  node_4_tax_engine: { th: "เครื่องคำนวณภาษี", en: "Tax Engine" },
  node_5_fund_recommender: { th: "ผู้แนะนำกองทุน", en: "Fund Recommender" },
  node_6_explanation: { th: "ผู้สรุปคำอธิบาย", en: "Explanation Agent" },
  node_7_human_review: { th: "การตรวจทานโดยมนุษย์", en: "Human Review" },
  node_8_compliance: { th: "ผู้ตรวจสอบกำกับ (SEC)", en: "Compliance Auditor" },
  node_9_report: { th: "ผู้จัดทำรายงาน", en: "Report Builder" },
};
const friendlyAgent = (code: string | null | undefined, lang: "th" | "en"): string => {
  if (!code) return "";
  const hit = AGENT_NAMES[code];
  if (hit) return hit[lang];
  // Fallback: strip the node_N_ prefix and prettify the remainder.
  return code.replace(/^node_\d+_/, "").replace(/_/g, " ");
};

// Group recommended funds by tax-deduction type (SSF / RMF / ThaiESG / other).
const FUND_TYPE_ORDER = ["SSF", "RMF", "ThaiESG"];
const groupFundsByType = (funds: any[]): { type: string; funds: any[] }[] => {
  const groups: Record<string, any[]> = {};
  for (const f of funds || []) {
    const t = (f.fund_type || "Other").toString();
    (groups[t] ||= []).push(f);
  }
  const ordered = FUND_TYPE_ORDER.filter((t) => groups[t]);
  const extras = Object.keys(groups).filter((t) => !FUND_TYPE_ORDER.includes(t));
  return [...ordered, ...extras].map((type) => ({ type, funds: groups[type] }));
};

// Licensed-advisor (CFA) contact surfaced by the "Contact Advisor" buttons.
// TODO(ship): replace `channel` with the real Line/phone/email before launch.
const CFA_CONTACT = {
  th: "ทีมที่ปรึกษาการเงินที่มีใบอนุญาต (CFA)",
  en: "Licensed Financial Advisor Team (CFA)",
  channel: "<TODO: ใส่ช่องทางติดต่อจริง (Line / โทร / อีเมล)>",
};

// Tracked profile fields the client did NOT provide (from extracted entities).
function getMissingFields(result: any) {
  const ent = result?.typhoon_result?.entities || {};
  return PROFILE_FIELDS.filter((f) => {
    if (f.key === "monthly_income") return ent.monthly_income == null && ent.annual_income == null;
    return ent[f.key] === null || ent[f.key] === undefined;
  });
}

// Uncertainty-Quantification (UQ) audit: a transparent confidence score for the
// whole advisory run, derived from signals the pipeline already produced.
function computeAudit(result: any) {
  const t = result?.typhoon_result;
  const conf = Math.round((t?.confidence ?? 0) * 100);
  const missingFields = getMissingFields(result);
  const penaltySum = missingFields.reduce((s, f) => s + f.penalty, 0);
  const completeness = Math.max(0, 100 - penaltySum);
  const comp = result?.compliance;
  const critIssues = (comp?.issues ?? []).filter((i: any) => i.severity === "critical").length;
  const complianceScore = comp
    ? (comp.approved ? 100 : Math.max(30, 100 - critIssues * 30))
    : 70;
  const funds = result?.recommendation?.recommended_funds?.length ?? 0;
  const fit = funds > 0 ? 100 : 50;
  const factors = [
    { label: "NLP Extraction Confidence", value: conf, weight: 0.30, note: "Typhoon interpreter certainty" },
    { label: "Profile Completeness", value: completeness, weight: 0.30, note: missingFields.length ? `${missingFields.length} field(s) missing` : "All key fields present" },
    { label: "Compliance Integrity", value: complianceScore, weight: 0.25, note: comp ? (comp.approved ? "No critical issues" : `${critIssues} critical issue(s)`) : "Pending advisor approval" },
    { label: "Recommendation Coverage", value: fit, weight: 0.15, note: funds ? `${funds} fund(s) matched` : "No funds matched" },
  ];
  const score = Math.round(factors.reduce((s, f) => s + f.value * f.weight, 0));
  return { score, factors, missingFields, completeness };
}

// Explainable-AI decision timeline: maps the structured run into transparent
// phases (Evidence -> Conclusion), derived deterministically from the result.
function buildDecisionTimeline(result: any, auditScore: number | null) {
  const c = result?.client_data;
  const t = result?.typhoon_result;
  const s = result?.suitability;
  const tax = result?.tax_result;
  const dc = tax?.detailed_calculations || {};
  const op = dc.optimization_purchases || {};
  const funds = result?.recommendation?.recommended_funds || [];
  const comp = result?.compliance;
  const b = (n: any) => "฿" + new Intl.NumberFormat("en-US").format(Math.round(n || 0));
  const missingFields = getMissingFields(result);

  return [
    {
      title: "Investor Understanding",
      evidence: [
        c ? `Income ${b(c.monthly_income)}/mo${c.bonus_months ? ` + ${c.bonus_months}-month bonus` : ""}` : "Income information",
        c ? `Existing benefits: RMF ${b(c.existing_rmf)}, SSF ${b(c.existing_ssf)}, insurance ${b(c.life_insurance)}` : "Existing tax benefits",
        `Risk preference: ${c?.risk_profile ?? "—"}`,
        t ? `NLP confidence: ${(t.confidence * 100).toFixed(0)}%` : null,
        ...missingFields.slice(0, 4).map((f) => `${f.label.replace(/ \(.*\)/, "")}: -`),
      ].filter(Boolean) as string[],
      conclusion: [
        `${c?.risk_profile ?? "Moderate"}-risk investor`,
        `Objective: ${c?.goal ?? "Tax optimization"}`,
        ...(missingFields.length
          ? ["Some profile parameters are missing", "Confidence reduced due to incomplete profile"]
          : []),
      ],
    },
    {
      title: "Suitability Assessment",
      evidence: [
        `Risk profile: ${s?.risk_profile ?? c?.risk_profile ?? "—"}`,
        `Investment horizon: ${s?.investment_horizon ?? "—"}`,
      ],
      conclusion: [
        s?.recommended_allocation
          ? `Suitable allocation: ${Object.entries(s.recommended_allocation).map(([k, v]) => `${Array.isArray(v) ? `${v[0]}–${v[1]}` : v}% ${k}`).join(" / ")}`
          : "Allocation determined",
      ],
    },
    {
      title: "Tax Optimization",
      evidence: [
        dc.assessable_income ? `Assessable income ${b(dc.assessable_income)}` : "Income level",
        `Existing deductions ${b(dc.deductions_before)}`,
      ],
      conclusion: tax
        ? [
            `Tax ${b(tax.tax_before)} → ${b(tax.tax_after)} (save ${b(tax.saving)})`,
            `Requires ${b(op.total_additional_investment)} additional tax-deductible investment`,
          ]
        : ["Additional tax-saving opportunity identified"],
    },
    {
      title: "Fund Screening",
      evidence: [
        "Risk-matched fund universe (SSF / RMF / ThaiESG)",
        "SEC compliance constraints",
      ],
      conclusion: [
        `${funds.length} fund(s) matched requirements`,
        ...funds.slice(0, 3).map((f: any) => `${f.fund_code} · ${f.fund_type} · risk ${f.risk_level}`),
      ],
    },
    {
      title: "Human Oversight",
      evidence: [
        "Portfolio recommendation",
        auditScore != null ? `Audit confidence: ${auditScore}%` : "Audit confidence score",
      ],
      conclusion: [
        comp
          ? (comp.approved
              ? "Compliance approved — cleared for final action"
              : `Rejected — ${(comp.issues ?? []).filter((i: any) => i.severity === "critical").length} critical issue(s) flagged`)
          : "Human review required before final action",
      ],
    },
  ];
}

// What-if CTA rendered under a chat bubble when the backend detector flags an
// "invest X" hypothetical. Holds its own editable amount so the client can
// tweak the prefilled number before re-running the deterministic pipeline.
function WhatIfCTA({
  label,
  initialAmount,
  disabled,
  onRun,
}: {
  label: string;
  initialAmount: number | null | undefined;
  disabled?: boolean;
  onRun: (amount: number) => void;
}) {
  const [amount, setAmount] = useState<string>(
    initialAmount != null ? String(Math.round(initialAmount)) : ""
  );
  const numeric = Number(amount.replace(/,/g, ""));
  const valid = Number.isFinite(numeric) && numeric > 0;
  return (
    <div className="mt-2 max-w-[85%] rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-3 flex flex-col gap-2">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-indigo-300/80 font-outfit">
        <RefreshCw className="h-3 w-3" /> reanalyze_form
      </div>
      <label className="text-[11px] text-slate-400">จำนวนเงินลงทุน (บาท)</label>
      <input
        type="text"
        inputMode="numeric"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        placeholder="เช่น 350000"
        disabled={disabled}
        className="bg-white/5 border border-white/10 rounded-md px-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/40 disabled:opacity-50"
      />
      <button
        onClick={() => valid && onRun(numeric)}
        disabled={disabled || !valid}
        className="flex items-center justify-center gap-1.5 bg-indigo-500/20 text-indigo-200 border border-indigo-500/30 rounded-md px-3 py-2 text-xs font-medium hover:bg-indigo-500/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <RefreshCw className="h-3.5 w-3.5" /> {label}
      </button>
    </div>
  );
}

export function DashboardShell({ view }: { view: "intake" | "results" | "chat" }) {
  const router = useRouter();
  const { setSessionId, lang } = useSession();
  const [contactOpen, setContactOpen] = useState(false);
  const [inputText, setInputText] = useState(PRESETS[0].text);
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [error, setError] = useState<string | null>(null);
  
  // Results State
  const [result, setResult] = useState<any>(null);
  // Raw execution log toggle (under the decision timeline)
  const [rawLogOpen, setRawLogOpen] = useState(false);
  // Optional supplemental values the user types for missing profile fields
  const [optionalInputs, setOptionalInputs] = useState<Record<string, string>>({});
  // Whether the advisor has generated the client proposal
  const [proposalDone, setProposalDone] = useState(false);

  // Client-facing chat (grounded in the session's pipeline output)
  type SuggestedAction = {
    type: string;
    label: string;
    prefill?: { investment_amount?: number | null };
    contact_method?: string;
  } | null;
  const [chatMessages, setChatMessages] = useState<{ role: "user" | "bot"; text: string; action?: SuggestedAction }[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  const handleSendChat = async () => {
    const q = chatInput.trim();
    if (!q || !result?.session_id) return;
    setChatMessages((prev) => [...prev, { role: "user", text: q }]);
    setChatInput("");
    setChatLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: result.session_id, message: q }),
      });
      const data = await res.json();
      const reply = res.ok ? (data.reply || "(ไม่มีคำตอบ)") : (data.detail || `เกิดข้อผิดพลาด (${res.status})`);
      setChatMessages((prev) => [...prev, { role: "bot", text: reply, action: res.ok ? (data.suggested_action ?? null) : null }]);
    } catch {
      setChatMessages((prev) => [...prev, { role: "bot", text: "เชื่อมต่อเซิร์ฟเวอร์ไม่สำเร็จ" }]);
    } finally {
      setChatLoading(false);
    }
  };

  // What-if CTA: re-run the deterministic pipeline with the hypothetical amount.
  // Per product decision, an "invest X" what-if is modelled as a 50/50 split
  // across SSF + RMF (both are real Typhoon entity override keys). The numbers
  // still come only from the Tax Engine re-run — never from the chat layer.
  const handleWhatIfReanalyze = (amount: number) => {
    if (!Number.isFinite(amount) || amount <= 0) return;
    const half = Math.round(amount / 2);
    handleRunWorkflow(undefined, { ssf: half, rmf: amount - half });
  };

  // File upload state
  const [fileLoading, setFileLoading] = useState(false);
  const [fileInfo, setFileInfo] = useState<string | null>(null);

  // Which audit card is expanded ('compliance' | 'uq' | null)
  const [auditOpen, setAuditOpen] = useState<null | "compliance" | "uq">(null);
  // Tax calculation breakdown expanded?
  const [taxOpen, setTaxOpen] = useState(false);

  const handleFileUpload = async (file?: File) => {
    if (!file) return;
    setFileLoading(true);
    setError(null);
    setFileInfo(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API_URL}/api/v1/extract-file`, { method: "POST", body: fd });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `Extraction failed (status ${res.status})`);
      }
      const data = await res.json();
      setInputText(data.extracted_text || "");
      setFileInfo(`Extracted from ${data.source} · review and edit before running`);
    } catch (err: any) {
      setError(err.message || "Failed to read the file.");
    } finally {
      setFileLoading(false);
    }
  };

  const handleRunWorkflow = async (textOverride?: string, overrides?: Record<string, any>) => {
    const inputForRun = typeof textOverride === "string" ? textOverride : inputText;
    setLoading(true);
    setError(null);
    setResult(null);
    setStatusText("Initializing LangGraph Orchestrator...");
    
    try {
      setStatusText("Agent 1: Interpreting Thai financial conversation (Typhoon)...");
      const response = await fetch(`${API_URL}/api/v1/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          raw_input_text: inputForRun,
          ...(overrides && Object.keys(overrides).length ? { overrides } : {}),
        })
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const data = await response.json();

      // Auto-continue through the SEC compliance audit so the result lands
      // directly on the post-audit state (no manual approval checkpoint).
      let finalData = data;
      if (data?.status === "awaiting_review" && data?.session_id) {
        setStatusText("Running SEC compliance audit...");
        const rec = await fetch(`${API_URL}/api/v1/recommend`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: data.session_id }),
        });
        if (rec.ok) {
          finalData = await rec.json();
        }
      }
      setResult(finalData);
    } catch (err: any) {
      setError(err.message || "Failed to connect to backend server. Make sure FastAPI is running on port 8000.");
    } finally {
      setLoading(false);
      setStatusText("");
    }
  };

  // Append any optional profile values the advisor filled in, then re-run the
  // analysis (a fresh session) so the supplemental data is incorporated.
  const applyOptionalInfo = () => {
    if (!result) return;
    const overrides: Record<string, any> = {};
    for (const f of getMissingFields(result)) {
      const raw = optionalInputs[f.key];
      if (raw == null || String(raw).trim() === "") continue;
      if (f.type === "number") {
        const n = Number(raw);
        if (!Number.isNaN(n)) overrides[f.key] = n; // 0 is a valid, authoritative value
      } else {
        overrides[f.key] = String(raw).trim();
      }
    }
    if (!Object.keys(overrides).length) return;
    setOptionalInputs({});
    // Re-run a fresh analysis with the values treated as ground truth (no LLM re-extraction).
    handleRunWorkflow(undefined, overrides);
  };

  // Generate a client proposal as a downloadable file. Does NOT send anything
  // externally — sending stays a deliberate advisor action.
  const handleGenerateProposal = () => {
    if (!result) return;
    const f = (n: any) => "THB " + new Intl.NumberFormat("en-US").format(Math.round(n || 0));
    const c = result.client_data || {};
    const tax = result.tax_result || {};
    const funds = result.recommendation?.recommended_funds || [];
    const lines = [
      "WEALTH ADVISORY PROPOSAL",
      "Session: " + result.session_id,
      "Generated: " + new Date().toLocaleString(),
      "",
      "CLIENT PROFILE",
      "  Age: " + (result.typhoon_result?.entities?.age ?? "-"),
      "  Risk profile: " + (c.risk_profile ?? "-"),
      "  Goal: " + (c.goal ?? "-"),
      "",
      "TAX OPTIMIZATION",
      "  Tax before: " + f(tax.tax_before),
      "  Tax after:  " + f(tax.tax_after),
      "  Tax saved:  " + f(tax.saving),
      "",
      "RECOMMENDED PORTFOLIO",
      ...funds.map((x: any) => `  - ${x.fund_code} (${x.fund_type}) ${f(x.amount_thb)} | risk ${x.risk_level}`),
      "",
      "COMPLIANCE: " + (result.compliance ? (result.compliance.approved ? "APPROVED" : "REJECTED") : "pending"),
      "",
      "Disclaimer: Mutual fund investments involve risk. Returns are not guaranteed.",
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `proposal-${result.session_id}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setProposalDone(true);
  };

  // Return to the intake form to revise (input text is preserved).
  const handleEditRecommendation = () => {
    setResult(null);
    setError(null);
    setProposalDone(false);
    try { sessionStorage.removeItem(RESULT_STORE_KEY); } catch { /* ignore */ }
  };

  // Hydrate the last analysis on first mount of a page that has none yet
  // (landing directly on /results or /chat, or after a refresh).
  useEffect(() => {
    if (result) return;
    try {
      const raw = sessionStorage.getItem(RESULT_STORE_KEY);
      if (raw) setResult(JSON.parse(raw));
    } catch { /* ignore */ }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist the latest analysis + expose the session id to the Nav so the chat
  // button enables and the result survives navigation/refresh.
  useEffect(() => {
    setSessionId(result?.session_id ?? null);
    try {
      if (result) sessionStorage.setItem(RESULT_STORE_KEY, JSON.stringify(result));
    } catch { /* ignore */ }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result]);

  // Helper to format currency
  const formatTHB = (val?: number) => {
    if (val === undefined || val === null) return "฿0.00";
    return new Intl.NumberFormat('th-TH', { style: 'currency', currency: 'THB' }).format(val);
  };

  const audit = result ? computeAudit(result) : null;

  return (
    <div className="relative">
      {/* Background Decorative Blobs */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-900/10 rounded-full blur-3xl pointer-events-none animate-pulse-slow"></div>
      <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-emerald-900/10 rounded-full blur-3xl pointer-events-none animate-pulse-slow" style={{ animationDelay: '2s' }}></div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8">

        {/* ===== INTAKE VIEW ===== */}
        {view === "intake" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-6xl mx-auto">
          {/* Left: transcription / presets / upload / run */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            <div className="glass-panel p-6 glow-indigo flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold tracking-wider text-indigo-400 uppercase font-outfit">{lang === "th" ? "ข้อความจากลูกค้า (ไทย)" : "Client Transcription (Thai)"}</h2>
                <Coins className="h-4 w-4 text-slate-400" />
              </div>
              <p className="text-xs text-slate-400">
                Paste client descriptions or conversations. The Typhoon model translates and extracts details before reasoning.
              </p>

              {/* Presets */}
              <div className="flex flex-col gap-2 mt-2">
                <span className="text-[10px] uppercase font-bold text-slate-500">{lang === "th" ? "ตัวอย่างข้อมูล" : "Intake Presets"}</span>
                <div className="flex flex-col gap-1.5">
                  {PRESETS.map((p, idx) => (
                    <button
                      key={idx}
                      onClick={() => setInputText(p.text)}
                      className={`text-left text-xs px-3 py-2 rounded-md transition-colors border ${
                        inputText === p.text 
                          ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300 font-semibold' 
                          : 'bg-slate-900/50 border-white/5 text-slate-300 hover:bg-slate-800/40'
                      }`}
                    >
                      {p.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* File Upload */}
              <div className="flex flex-col gap-2 mt-2">
                <span className="text-[10px] uppercase font-bold text-slate-500">{lang === "th" ? "หรืออัปโหลดเอกสาร" : "Or upload a document"}</span>
                <label
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    handleFileUpload(e.dataTransfer.files?.[0]);
                  }}
                  className="cursor-pointer border border-dashed border-white/15 hover:border-indigo-500 rounded-lg p-4 flex flex-col items-center justify-center gap-1.5 text-center transition-colors bg-slate-950/40"
                >
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    className="hidden"
                    onChange={(e) => handleFileUpload(e.target.files?.[0] ?? undefined)}
                  />
                  {fileLoading ? (
                    <>
                      <RefreshCw className="h-5 w-5 text-indigo-400 animate-spin" />
                      <span className="text-xs text-indigo-300">Reading document (Typhoon vision)…</span>
                    </>
                  ) : (
                    <>
                      <FileSpreadsheet className="h-5 w-5 text-slate-400" />
                      <span className="text-xs text-slate-400">Click or drag a file here</span>
                      <span className="text-[10px] text-slate-600">PDF · JPG · PNG — payslip, tax form, fund statement</span>
                    </>
                  )}
                </label>
                {fileInfo && (
                  <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                    <CheckCircle className="h-3 w-3" /> {fileInfo}
                  </span>
                )}
              </div>

              {/* Input Textarea */}
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                className="w-full h-44 mt-2 p-3 bg-slate-950/70 border border-white/5 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors resize-none font-mono"
                placeholder="Type client description..."
              />

              {/* Trigger Button */}
              <button
                onClick={() => handleRunWorkflow()}
                disabled={loading}
                className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium text-sm rounded-lg transition-colors flex items-center justify-center gap-2 mt-2 shadow-lg shadow-indigo-600/20"
              >
                {loading ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>{lang === "th" ? "กำลังประมวลผล..." : "Processing Agents..."}</span>
                  </>
                ) : (
                  <>
                    <span>{lang === "th" ? "วิเคราะห์ข้อมูล" : "Run Orchestrator Loop"}</span>
                  </>
                )}
              </button>

              {/* State Trace Indicators */}
              {loading && (
                <div className="mt-2 p-3 bg-slate-950/40 border border-white/5 rounded-lg flex flex-col gap-2">
                  <div className="flex items-center gap-2 text-xs text-indigo-400 font-medium">
                    <RefreshCw className="h-3 w-3 animate-spin" />
                    <span>{statusText}</span>
                  </div>
                </div>
              )}

              {error && (
                <div className="mt-2 p-3 bg-red-950/20 border border-red-500/20 rounded-lg flex items-start gap-2.5">
                  <ShieldAlert className="h-4 w-4 text-red-500 mt-0.5 animate-pulse" />
                  <div className="text-xs text-red-300">
                    <p className="font-semibold">Error Occurred</p>
                    <p className="mt-0.5">{error}</p>
                  </div>
                </div>
              )}
            </div>
            
            {/* Catalog Info Box */}
            <div className="glass-panel p-5 border-white/5 flex flex-col gap-3">
              <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">{lang === "th" ? "สถานะระบบ" : "System Status"}</h3>
              <div className="flex flex-col gap-2.5 text-xs">
                <div className="flex justify-between border-b border-white/5 pb-1.5">
                  <span className="text-slate-400">Typhoon NLP Engine</span>
                  <span className="text-emerald-400 font-mono">Active (Fallback Mock/Live)</span>
                </div>
                <div className="flex justify-between border-b border-white/5 pb-1.5">
                  <span className="text-slate-400">Qwen Advisory Agents</span>
                  <span className="text-emerald-400">Groq API Enabled</span>
                </div>
                <div className="flex justify-between border-b border-white/5 pb-1.5">
                  <span className="text-slate-400">Tax Optimizer Core</span>
                  <span className="text-indigo-400 font-semibold">Deterministic Python</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Audit & Log persist</span>
                  <span className="text-emerald-400">Write-Ahead SQLite</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right: post-analysis actions — missing-info form (optional) + skip-to-results.
              Appears after Run; the form uses the same overrides re-analyze path. */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            {!result && (
              <div className="glass-panel p-6 border-dashed border-white/10 flex flex-col items-center justify-center text-center gap-3 min-h-[200px]">
                <FileText className="h-7 w-7 text-indigo-400/70" />
                <p className="text-xs text-slate-400 max-w-xs">
                  {lang === "th" ? "กด “วิเคราะห์ข้อมูล” เพื่อเริ่ม ระบบจะแสดงข้อมูลที่ขาด (ถ้ามี) ที่นี่" : "Run the analysis to start. Any missing profile info will appear here."}
                </p>
              </div>
            )}

            {result && audit && audit.missingFields.length > 0 && (
              <div className="glass-panel p-6 border border-amber-500/20 bg-amber-500/[0.03] flex flex-col gap-4">
                <div className="flex items-start gap-2.5">
                  <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <h3 className="text-sm font-semibold text-amber-300">{lang === "th" ? "ข้อมูลโปรไฟล์ที่ขาด (ไม่บังคับ)" : "Missing Profile Information (Optional)"}</h3>
                    <p className="text-xs text-slate-400 mt-1">
                      {lang === "th" ? "ข้อมูลต่อไปนี้ยังไม่ได้ระบุ การเพิ่มจะช่วยให้คำแนะนำแม่นยำขึ้น หรือข้ามไปดูผลลัพธ์ได้เลย" : "Not provided yet. Adding these improves accuracy — or skip ahead to the results."}
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {audit.missingFields.map((f) => (
                    <div key={f.key} className="flex flex-col gap-1">
                      <label className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">{f.label}</label>
                      <input
                        type={f.type}
                        value={optionalInputs[f.key] ?? ""}
                        onChange={(e) => setOptionalInputs({ ...optionalInputs, [f.key]: e.target.value })}
                        placeholder={f.placeholder}
                        className="w-full px-3 py-2 bg-slate-950/70 border border-white/10 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-amber-500/50 transition-colors"
                      />
                    </div>
                  ))}
                </div>
                <button
                  onClick={applyOptionalInfo}
                  disabled={loading}
                  className="px-4 py-2.5 bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-200 text-xs font-semibold rounded-lg disabled:opacity-50 flex items-center justify-center gap-1.5"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
                  {lang === "th" ? "บันทึกและวิเคราะห์ใหม่" : "Apply & re-analyze"}
                </button>
              </div>
            )}

            {result && audit && audit.missingFields.length === 0 && (
              <div className="glass-panel p-6 border border-emerald-500/20 bg-emerald-500/[0.03] flex items-start gap-2.5">
                <CheckCircle className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                <p className="text-xs text-slate-300">{lang === "th" ? "ข้อมูลครบถ้วน พร้อมดูผลการวิเคราะห์" : "Profile complete — ready to view the full results."}</p>
              </div>
            )}

            {result && (
              <button
                onClick={() => router.push("/results")}
                className="w-full py-3 bg-emerald-600/90 hover:bg-emerald-500 text-white font-medium text-sm rounded-lg transition-colors flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20"
              >
                {tr(lang, "goToResults")} →
              </button>
            )}
          </div>
        </div>
        )}

        {/* ===== RESULTS VIEW ===== */}
        {view === "results" && (
        <div className="max-w-5xl mx-auto">
          {/* Incomplete sessions: the sections below already self-gate on
              tax_result/recommendation existing, so only the interpreter panel
              + clarification banner render — no None-data reaches them. */}
          {result && !isSessionComplete(result) && (
            <div className="mb-6 p-5 bg-amber-500/[0.06] border border-amber-500/30 rounded-xl flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-sm text-amber-300">{tr(lang, "incompleteTitle")}</h3>
                <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">{tr(lang, "incompleteBody")}</p>
              </div>
            </div>
          )}
          {/* Results & Analytics */}
          <div className="flex flex-col gap-6">
            
            {/* If no result exists */}
            {!result && !loading && (
              <div className="glass-panel p-16 flex flex-col items-center justify-center text-center gap-4 border-dashed border-white/10 min-h-[500px]">
                <div className="p-4 bg-slate-900/60 rounded-full border border-white/5">
                  <FileText className="h-8 w-8 text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold tracking-tight text-slate-300">Awaiting Advice Session</h3>
                  <p className="text-sm text-slate-400 max-w-sm mt-1 mx-auto">
                    Fill out the client intake form on the left and start the LangGraph workflow to view tax optimization metrics, Typhoon interpreter NLP, and compliance audits.
                  </p>
                </div>
              </div>
            )}

            {/* Loading Placeholder */}
            {loading && !result && (
              <div className="glass-panel p-16 flex flex-col items-center justify-center text-center gap-4 min-h-[500px]">
                <RefreshCw className="h-8 w-8 text-indigo-500 animate-spin" />
                <p className="text-sm text-indigo-400 font-mono tracking-wider">{statusText}</p>
              </div>
            )}

            {/* Results Renders */}
            {result && (
              <div className="flex flex-col gap-6">
                
                {/* Post-approval confirmation (appears after the compliance audit) */}
                {result.compliance && result.status !== "awaiting_review" && (
                  result.compliance.approved ? (
                    <div className="p-6 bg-slate-900/40 border border-emerald-500/25 rounded-xl flex flex-col gap-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="font-semibold text-base text-slate-100">{lang === "th" ? "ผ่านการตรวจสอบกำกับ" : "Compliance approved"}</h3>
                          <p className="text-xs text-slate-400 mt-1 max-w-md">
                            Audit confirmed. The advisor has signed off on this recommendation.
                          </p>
                        </div>
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 shrink-0">
                          <CheckCircle className="h-3.5 w-3.5" /> Approved
                        </span>
                      </div>
                      <div className="flex flex-col sm:flex-row sm:justify-end items-stretch sm:items-center gap-2">
                        <button
                          onClick={handleEditRecommendation}
                          className="px-4 py-2.5 bg-slate-800/60 hover:bg-slate-700/60 border border-white/10 text-slate-200 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5"
                        >
                          <Pencil className="h-3.5 w-3.5" /> {lang === "th" ? "แก้ไขคำแนะนำ" : "Edit recommendation"}
                        </button>
                        <button
                          onClick={() => setContactOpen((v) => !v)}
                          className="px-4 py-2.5 bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-200 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5"
                        >
                          <MessageCircle className="h-3.5 w-3.5" /> {lang === "th" ? "ติดต่อที่ปรึกษา" : "Contact Advisor"}
                        </button>
                        <button
                          onClick={handleGenerateProposal}
                          className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-indigo-600/20 flex items-center justify-center gap-1.5"
                        >
                          {proposalDone ? <CheckCircle className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                          {proposalDone ? (lang === "th" ? "ดาวน์โหลดแล้ว" : "Downloaded") : (lang === "th" ? "ดาวน์โหลดสรุป" : "Download summary")}
                        </button>
                      </div>
                      {contactOpen && (
                        <div className="p-3 bg-amber-500/[0.06] border border-amber-500/25 rounded-lg text-xs text-amber-200 sm:text-right break-all">
                          {CFA_CONTACT[lang]} — {CFA_CONTACT.channel}
                        </div>
                      )}
                      {proposalDone && (
                        <p className="text-[11px] text-emerald-400/90 sm:text-right">
                          {lang === "th" ? "ดาวน์โหลดสรุปแล้ว — พร้อมส่งให้ลูกค้า" : "Summary downloaded — ready to send to the client."}
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="p-6 bg-slate-900/40 border border-red-500/25 rounded-xl flex flex-col gap-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="font-semibold text-base text-slate-100">{lang === "th" ? "ไม่ผ่านการตรวจสอบกำกับ" : "Compliance rejected"}</h3>
                          <p className="text-xs text-slate-400 mt-1 max-w-md">
                            The audit flagged {result.compliance.issues?.length ?? 0} issue(s). Revise the recommendation before proceeding.
                          </p>
                        </div>
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/15 text-red-400 border border-red-500/25 shrink-0">
                          <ShieldAlert className="h-3.5 w-3.5" /> Rejected
                        </span>
                      </div>
                      <div className="flex flex-col sm:flex-row sm:justify-end items-stretch sm:items-center gap-2">
                        <button
                          onClick={handleEditRecommendation}
                          className="px-4 py-2.5 bg-slate-800/60 hover:bg-slate-700/60 border border-white/10 text-slate-200 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5"
                        >
                          <Pencil className="h-3.5 w-3.5" /> {lang === "th" ? "แก้ไขคำแนะนำ" : "Edit recommendation"}
                        </button>
                        <button
                          onClick={() => setContactOpen((v) => !v)}
                          className="px-4 py-2.5 bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-200 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5"
                        >
                          <MessageCircle className="h-3.5 w-3.5" /> {lang === "th" ? "ติดต่อที่ปรึกษา" : "Contact Advisor"}
                        </button>
                      </div>
                      {contactOpen && (
                        <div className="p-3 bg-amber-500/[0.06] border border-amber-500/25 rounded-lg text-xs text-amber-200 sm:text-right break-all">
                          {CFA_CONTACT[lang]} — {CFA_CONTACT.channel}
                        </div>
                      )}
                    </div>
                  )
                )}

                {/* Clarification needed (early stop: ambiguous / missing-critical / risk conflict) */}
                {(result.status === "needs_clarification" || result.status === "needs_review") && (
                  <div className="p-5 bg-amber-500/[0.06] border border-amber-500/30 rounded-xl flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <h3 className="font-semibold text-sm text-amber-300">
                        {result.status === "needs_review" ? "Advisor confirmation needed" : "More information needed before we can proceed"}
                      </h3>
                      <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
                        {result.typhoon_result?.clarification_needed
                          || result.suitability?.review_reason
                          || "The workflow paused before completing because the profile is incomplete or ambiguous — by design, it never guesses missing client data. Add the details below and re-analyze."}
                      </p>
                    </div>
                  </div>
                )}

                {/* 1. Client Info Summary (shows what the client actually provided; "-" if not) */}
                <div className="glass-panel p-6 border-white/5 grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">{lang === "th" ? "อายุลูกค้า" : "Client Age"}</span>
                    <span className="text-lg font-semibold text-slate-200">
                      {result.typhoon_result?.entities?.age != null ? `${result.typhoon_result.entities.age} Years Old` : "-"}
                    </span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">{lang === "th" ? "เงินได้ที่ประเมิน" : "Assessable Income"}</span>
                    <span className="text-lg font-semibold text-slate-200">
                      {(result.typhoon_result?.entities?.monthly_income != null || result.typhoon_result?.entities?.annual_income != null) && result.client_data
                        ? formatTHB((result.client_data.monthly_income * 12) + (result.client_data.monthly_income * result.client_data.bonus_months))
                        : "-"
                      }
                    </span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">{lang === "th" ? "ระดับความเสี่ยง" : "Risk Profile"}</span>
                    <span className="text-lg font-semibold text-indigo-400">{dash(result.typhoon_result?.entities?.risk_profile)}</span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">{lang === "th" ? "เป้าหมายการเงิน" : "Financial Goal"}</span>
                    <span className="text-lg font-semibold text-emerald-400">{dash(result.typhoon_result?.entities?.goal)}</span>
                  </div>
                </div>

                {/* (Missing Profile Information form moved to the Intake page —
                    shown there in the right column after Run.) */}

                {/* 1b. Audit Summary — clickable Compliance + UQ cards */}
                {audit && (
                  <div className="flex flex-col gap-3">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Compliance card */}
                      <button
                        onClick={() => setAuditOpen(auditOpen === "compliance" ? null : "compliance")}
                        className="glass-panel p-5 border-white/5 text-left hover:border-white/20 transition-colors flex items-center justify-between gap-3"
                      >
                        <div className="flex items-center gap-3">
                          {result.compliance ? (
                            result.compliance.approved ? (
                              <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg border border-emerald-500/20"><ShieldCheck className="h-6 w-6" /></div>
                            ) : (
                              <div className="p-2 bg-red-500/10 text-red-400 rounded-lg border border-red-500/20"><ShieldAlert className="h-6 w-6" /></div>
                            )
                          ) : (
                            <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg border border-amber-500/20"><Clock className="h-6 w-6" /></div>
                          )}
                          <div>
                            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Compliance</p>
                            <p className={`text-lg font-bold ${result.compliance ? (result.compliance.approved ? "text-emerald-400" : "text-red-400") : "text-amber-400"}`}>
                              {result.compliance ? (result.compliance.approved ? (lang === "th" ? "ผ่าน" : "Compliant") : (lang === "th" ? "ไม่ผ่าน" : "Violation")) : (lang === "th" ? "รอตรวจ" : "Pending")}
                            </p>
                          </div>
                        </div>
                        <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform ${auditOpen === "compliance" ? "rotate-180" : ""}`} />
                      </button>

                      {/* UQ audit card */}
                      <button
                        onClick={() => setAuditOpen(auditOpen === "uq" ? null : "uq")}
                        className="glass-panel p-5 border-white/5 text-left hover:border-white/20 transition-colors flex items-center justify-between gap-3"
                      >
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg border ${audit.score >= 80 ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : audit.score >= 60 ? "bg-amber-500/10 text-amber-400 border-amber-500/20" : "bg-red-500/10 text-red-400 border-red-500/20"}`}>
                            <Gauge className="h-6 w-6" />
                          </div>
                          <div>
                            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">{lang === "th" ? "ความเชื่อมั่น (UQ)" : "UQ Audit · Confidence"}</p>
                            <p className={`text-lg font-bold ${audit.score >= 80 ? "text-emerald-400" : audit.score >= 60 ? "text-amber-400" : "text-red-400"}`}>{audit.score}%</p>
                          </div>
                        </div>
                        <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform ${auditOpen === "uq" ? "rotate-180" : ""}`} />
                      </button>
                    </div>

                    {/* Compliance breakdown */}
                    {auditOpen === "compliance" && (
                      <div className="glass-panel p-5 border-white/5 flex flex-col gap-2">
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Compliance Breakdown</p>
                        {!result.compliance ? (
                          <p className="text-xs text-amber-300">The SEC audit runs once the profile is complete and the recommendation is generated.</p>
                        ) : result.compliance.issues?.length > 0 ? (
                          <div className="flex flex-col gap-1.5">
                            {result.compliance.issues.map((iss: any, i: number) => {
                              const crit = iss.severity === "critical";
                              return (
                                <div key={i} className={`p-2.5 rounded-md text-xs flex items-start gap-2 border ${crit ? "bg-red-500/5 border-red-500/15 text-red-300" : "bg-amber-500/5 border-amber-500/15 text-amber-300"}`}>
                                  <span className={`font-bold shrink-0 uppercase text-[10px] mt-0.5 ${crit ? "text-red-400" : "text-amber-400"}`}>{iss.severity}</span>
                                  <span>{iss.description}{iss.route_back_to ? <span className="text-slate-500"> · → {friendlyAgent(iss.route_back_to, lang)}</span> : null}</span>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="p-2.5 bg-emerald-500/5 border border-emerald-500/15 rounded-md text-xs text-emerald-300 flex items-center gap-2">
                            <CheckCircle className="h-4 w-4 shrink-0" /> All SEC checks passed — no return guarantees or risk mismatches.
                          </div>
                        )}
                      </div>
                    )}

                    {/* UQ breakdown */}
                    {auditOpen === "uq" && (
                      <div className="glass-panel p-5 border-white/5 flex flex-col gap-3">
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Uncertainty Breakdown · weighted to {audit.score}%</p>
                        {audit.factors.map((f, i) => (
                          <div key={i} className="flex flex-col gap-1">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-slate-300">{f.label} <span className="text-slate-600">· {Math.round(f.weight * 100)}% weight</span></span>
                              <span className="font-mono font-semibold text-slate-200">{f.value}%</span>
                            </div>
                            <div className="h-1.5 bg-slate-800/60 rounded-full overflow-hidden">
                              <div className={`h-full rounded-full ${f.value >= 80 ? "bg-emerald-500" : f.value >= 60 ? "bg-amber-500" : "bg-red-500"}`} style={{ width: `${f.value}%` }} />
                            </div>
                            <span className="text-[10px] text-slate-500">{f.note}</span>
                          </div>
                        ))}

                        {/* Confidence deductions from missing profile data */}
                        {audit.missingFields.length > 0 && (
                          <div className="mt-1 border-t border-white/5 pt-3 flex flex-col gap-1.5">
                            <p className="text-[10px] uppercase font-bold text-amber-400/80 tracking-wider">Profile Completeness — deductions</p>
                            <div className="flex items-center justify-between text-xs text-slate-400">
                              <span>Starting confidence</span><span className="font-mono">100%</span>
                            </div>
                            {audit.missingFields.map((f) => (
                              <div key={f.key} className="flex items-center justify-between text-xs">
                                <span className="text-slate-400">Missing {f.label.replace(/ \(.*\)/, "")}</span>
                                <span className="font-mono text-amber-400">−{f.penalty}%</span>
                              </div>
                            ))}
                            <div className="flex items-center justify-between text-xs font-semibold border-t border-white/5 pt-1.5 mt-0.5">
                              <span className="text-slate-300">Profile completeness</span>
                              <span className="font-mono text-slate-200">{audit.completeness}%</span>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* 2. Typhoon Pre-processing Layer Details */}
                {result.typhoon_result && (
                  <div className="glass-panel p-6 border-white/5 flex flex-col gap-4">
                    <div className="flex items-center justify-between border-b border-white/5 pb-3">
                      <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse"></div>
                        <h3 className="text-sm font-semibold tracking-wider text-indigo-400 uppercase font-outfit">{lang === "th" ? "ตัวแปลภาษาไทย Typhoon NLP" : "Typhoon Thai NLP Interpreter"}</h3>
                      </div>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                        result.typhoon_result.confidence >= 0.80 
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                          : 'bg-red-500/10 text-red-400 border border-red-500/20'
                      }`}>
                        {(result.typhoon_result.confidence * 100).toFixed(0)}% NLP Confidence
                      </span>
                    </div>

                    {result.typhoon_result.confidence < 0.80 && (
                      <div className="p-3.5 bg-red-950/20 border border-red-500/20 rounded-lg flex items-start gap-2.5">
                        <AlertTriangle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                        <div className="text-xs text-red-300">
                          <p className="font-semibold">Vague Input - Human Review Required</p>
                          <p className="mt-0.5">The NLP confidence level falls below the 0.80 quality standard. The orchestrator automatically paused the workflow for human verification.</p>
                        </div>
                      </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Left: Normalized Thai */}
                      <div className="p-4 bg-slate-950/40 border border-white/5 rounded-lg">
                        <h4 className="text-xs uppercase font-bold text-slate-500 tracking-wider">Normalized Thai Financial Text</h4>
                        <p className="text-xs text-slate-300 mt-2 leading-relaxed font-mono">
                          {result.typhoon_result.normalized_thai}
                        </p>
                      </div>

                      {/* Right: English Translation */}
                      <div className="p-4 bg-slate-950/40 border border-white/5 rounded-lg">
                        <h4 className="text-xs uppercase font-bold text-slate-500 tracking-wider">Financial English Translation</h4>
                        <p className="text-xs text-slate-300 mt-2 leading-relaxed italic font-mono">
                          "{result.typhoon_result.english_translation}"
                        </p>
                      </div>
                    </div>

                    {/* Missing fields detection */}
                    {result.typhoon_result.missing_information && result.typhoon_result.missing_information.length > 0 && (
                      <div className="p-3 bg-amber-500/5 border border-amber-500/15 rounded-lg flex items-start gap-2">
                        <Info className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                        <div className="text-xs text-amber-300">
                          <span className="font-semibold">Detected Missing Profile Parameters: </span>
                          <span className="font-mono text-slate-300 font-semibold">
                            {result.typhoon_result.missing_information.join(", ")}
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Entities details */}
                    {result.typhoon_result.entities && (
                      <div className="mt-1">
                        <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">{lang === "th" ? "ตารางค่าที่สกัดได้" : "Extracted Values Table"}</span>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {Object.entries(result.typhoon_result.entities).map(([key, val]: any) => {
                            if (val === null || val === undefined) return null;
                            let displayVal = val;
                            if (typeof val === 'number') {
                              if (key.includes('income') || key === 'rmf' || key === 'ssf' || key === 'life_insurance') {
                                displayVal = formatTHB(val);
                              }
                            }
                            return (
                              <div key={key} className="px-2.5 py-1 bg-slate-900/60 border border-white/5 rounded-md text-xs flex items-center gap-1.5 text-slate-300">
                                <span className="text-indigo-400 font-semibold">{key}:</span>
                                <span className="font-mono">{displayVal}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 3. Tax Comparison and Savings */}
                {result.tax_result && (
                  <>
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-6">

                    {/* Tax numbers */}
                    <div className="md:col-span-5 glass-panel p-6 border-white/5 flex flex-col justify-between gap-4">
                      <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">{lang === "th" ? "ผลการวางแผนภาษี" : "Tax Optimization Results"}</h3>
                      
                      <div className="flex flex-col gap-3">
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-slate-400">{lang === "th" ? "ภาษีก่อนปรับ:" : "Tax Before Optimization:"}</span>
                          <span className="font-semibold text-slate-300 font-mono">{formatTHB(result.tax_result.tax_before)}</span>
                        </div>
                        <div className="flex justify-between items-center text-sm border-b border-white/5 pb-3">
                          <span className="text-slate-400">{lang === "th" ? "ภาษีหลังปรับ:" : "Tax After Optimization:"}</span>
                          <span className="font-semibold text-slate-300 font-mono">{formatTHB(result.tax_result.tax_after)}</span>
                        </div>
                        <div className="flex justify-between items-center py-2">
                          <span className="text-emerald-400 font-semibold text-sm">{lang === "th" ? "ภาษีที่ประหยัด:" : "Tax Saved:"}</span>
                          <span className="font-bold text-lg text-emerald-400 font-mono">{formatTHB(result.tax_result.saving)}</span>
                        </div>
                      </div>

                      <div className="p-3 bg-emerald-500/5 border border-emerald-500/10 rounded-lg flex items-start gap-2.5">
                        <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                        <p className="text-[11px] text-emerald-300 leading-relaxed">
                          Deterministic calculations applied. Tax liability minimized from {formatTHB(result.tax_result.tax_before)} to {formatTHB(result.tax_result.tax_after)}.
                        </p>
                      </div>

                      <button
                        onClick={() => setTaxOpen(!taxOpen)}
                        className="flex items-center justify-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
                      >
                        {taxOpen ? "Hide" : "View"} calculation breakdown
                        <ChevronDown className={`h-3.5 w-3.5 transition-transform ${taxOpen ? "rotate-180" : ""}`} />
                      </button>
                    </div>

                    {/* SVG Chart Comparison */}
                    <div className="md:col-span-7 glass-panel p-6 border-white/5 flex flex-col gap-4">
                      <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">{lang === "th" ? "เปรียบเทียบ (บาท)" : "Visualized Comparison (THB)"}</h3>
                      
                      {/* SVG Chart */}
                      <div className="flex-1 flex items-end justify-around h-44 mt-2 border-b border-slate-700/30 pb-2 relative">
                        {/* Bar 1: Tax Before */}
                        <div className="flex flex-col items-center gap-2 w-16">
                          <span className="text-[10px] text-slate-400 font-mono">
                            {Math.round(result.tax_result.tax_before / 1000)}k
                          </span>
                          <div 
                            className="w-full bg-gradient-to-t from-red-600 to-red-400 rounded-t-md transition-all duration-500" 
                            style={{ 
                              height: `${Math.max((result.tax_result.tax_before / Math.max(result.tax_result.tax_before, 1)) * 100, 5)}px` 
                            }}
                          ></div>
                          <span className="text-[10px] font-semibold text-slate-400">Before</span>
                        </div>

                        {/* Bar 2: Tax After */}
                        <div className="flex flex-col items-center gap-2 w-16">
                          <span className="text-[10px] text-slate-400 font-mono">
                            {Math.round(result.tax_result.tax_after / 1000)}k
                          </span>
                          <div 
                            className="w-full bg-gradient-to-t from-indigo-600 to-indigo-400 rounded-t-md transition-all duration-500" 
                            style={{ 
                              height: `${Math.max((result.tax_result.tax_after / Math.max(result.tax_result.tax_before, 1)) * 100, 5)}px` 
                            }}
                          ></div>
                          <span className="text-[10px] font-semibold text-slate-400">After</span>
                        </div>

                        {/* Bar 3: Savings */}
                        <div className="flex flex-col items-center gap-2 w-16">
                          <span className="text-[10px] text-emerald-400 font-mono">
                            {Math.round(result.tax_result.saving / 1000)}k
                          </span>
                          <div 
                            className="w-full bg-gradient-to-t from-emerald-600 to-emerald-400 rounded-t-md transition-all duration-500" 
                            style={{ 
                              height: `${Math.max((result.tax_result.saving / Math.max(result.tax_result.tax_before, 1)) * 100, 5)}px` 
                            }}
                          ></div>
                          <span className="text-[10px] font-semibold text-emerald-400">Saved</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Tax calculation breakdown (expandable) */}
                  {taxOpen && result.tax_result.detailed_calculations && (() => {
                    const dc = result.tax_result.detailed_calculations;
                    const bd = dc.deduction_breakdown || {};
                    const taxableBefore = dc.taxable_before ?? (dc.assessable_income - dc.deductions_before);
                    const taxableAfter = dc.taxable_after ?? (dc.assessable_income - dc.deductions_after);
                    const rows = [
                      { label: "Assessable income", before: dc.assessable_income, after: dc.assessable_income },
                      { label: "− Personal allowance", before: bd.personal_allowance, after: bd.personal_allowance },
                      { label: "− Expense deduction (50%, capped)", before: bd.expense_deduction, after: bd.expense_deduction },
                      { label: "− Life / health insurance", before: bd.life_insurance, after: bd.life_insurance },
                      { label: "− SSF", before: bd.ssf_before, after: bd.ssf_after },
                      { label: "− RMF", before: bd.rmf_before, after: bd.rmf_after },
                      { label: "− ThaiESG", before: 0, after: bd.thaiesg_after },
                    ];
                    return (
                      <div className="glass-panel p-6 border-white/5 flex flex-col gap-3">
                        <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">Calculation Breakdown</h3>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm border-collapse">
                            <thead>
                              <tr className="text-slate-500 border-b border-white/5">
                                <th className="py-2 text-left font-semibold text-xs uppercase">Step</th>
                                <th className="py-2 text-right font-semibold text-xs uppercase">Before</th>
                                <th className="py-2 text-right font-semibold text-xs uppercase">After</th>
                              </tr>
                            </thead>
                            <tbody>
                              {rows.map((r, i) => (
                                <tr key={i} className="border-b border-white/5 text-slate-300">
                                  <td className="py-2 text-slate-400">{r.label}</td>
                                  <td className="py-2 text-right font-mono">{formatTHB(r.before)}</td>
                                  <td className="py-2 text-right font-mono">{formatTHB(r.after)}</td>
                                </tr>
                              ))}
                              <tr className="border-b border-white/5 text-slate-200 font-semibold">
                                <td className="py-2">= Taxable income</td>
                                <td className="py-2 text-right font-mono">{formatTHB(taxableBefore)}</td>
                                <td className="py-2 text-right font-mono">{formatTHB(taxableAfter)}</td>
                              </tr>
                              <tr className="text-slate-200 font-bold">
                                <td className="py-2">Progressive tax</td>
                                <td className="py-2 text-right font-mono text-red-400">{formatTHB(result.tax_result.tax_before)}</td>
                                <td className="py-2 text-right font-mono text-emerald-400">{formatTHB(result.tax_result.tax_after)}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                        <p className="text-[10px] text-slate-500 leading-relaxed">
                          Computed by the deterministic Thai PIT engine (progressive brackets). “After” maximizes SSF / RMF / ThaiESG within legal caps. Note: PVD and donations are not yet modeled.
                        </p>
                      </div>
                    );
                  })()}
                  </>
                )}

                {/* 4. Detailed Optimizations Investments */}
                {result.tax_result?.detailed_calculations?.optimization_purchases && (
                  <div className="glass-panel p-6 border-white/5 flex flex-col gap-4">
                    <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">{lang === "th" ? "เงินลงทุนที่ต้องใช้เพื่อประหยัดภาษี" : "Required Investments to achieve tax savings"}</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                      <div className="p-4 bg-slate-950/40 border border-white/5 rounded-lg">
                        <p className="text-xs text-slate-500 uppercase font-semibold font-outfit">Additional SSF Needed</p>
                        <p className="text-base font-bold font-mono text-slate-300 mt-1">
                          {formatTHB(result.tax_result.detailed_calculations.optimization_purchases.ssf_additional)}
                        </p>
                      </div>
                      <div className="p-4 bg-slate-950/40 border border-white/5 rounded-lg">
                        <p className="text-xs text-slate-500 uppercase font-semibold font-outfit">Additional RMF Needed</p>
                        <p className="text-base font-bold font-mono text-slate-300 mt-1">
                          {formatTHB(result.tax_result.detailed_calculations.optimization_purchases.rmf_additional)}
                        </p>
                      </div>
                      <div className="p-4 bg-slate-950/40 border border-white/5 rounded-lg">
                        <p className="text-xs text-slate-500 uppercase font-semibold font-outfit">ThaiESG Target Investment</p>
                        <p className="text-base font-bold font-mono text-slate-300 mt-1">
                          {formatTHB(result.tax_result.detailed_calculations.optimization_purchases.thaiesg_additional)}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* 5. Portfolio Fund Recommendations — grouped into a section per type */}
                {result.recommendation && (
                  <div className="glass-panel p-6 border-white/5 flex flex-col gap-4">
                    <div className="flex items-center justify-between border-b border-white/5 pb-3">
                      <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">{lang === "th" ? "พอร์ตกองทุนที่แนะนำ (แยกตามประเภท)" : "Recommended Portfolio (by Type)"}</h3>
                      <span className="text-xs text-slate-400">{lang === "th" ? "อิงตามความเสี่ยงและเป้าหมาย" : "Based on Risk profile & Goals"}</span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {groupFundsByType(result.recommendation.recommended_funds || []).map((grp) => {
                        const total = grp.funds.reduce((s: number, f: any) => s + (f.amount_thb || 0), 0);
                        return (
                          <div key={grp.type} className="p-4 bg-slate-950/40 border border-white/5 rounded-lg flex flex-col gap-3">
                            <div className="flex items-center justify-between border-b border-white/5 pb-2">
                              <span className="text-sm font-bold text-indigo-300">{grp.type}</span>
                              <span className="text-xs font-mono text-slate-400">{formatTHB(total)}</span>
                            </div>
                            <div className="flex flex-col gap-2.5">
                              {grp.funds.map((fund: any, idx: number) => (
                                <div key={idx} className="flex flex-col gap-1 border-b border-white/5 last:border-0 pb-2.5 last:pb-0">
                                  <div className="flex items-center justify-between gap-2">
                                    <span className="text-xs font-semibold text-slate-200">{fund.fund_code}</span>
                                    <span className="inline-block px-1.5 py-0.5 rounded text-[10px] bg-indigo-500/10 text-indigo-400 font-mono shrink-0">
                                      {lang === "th" ? "เสี่ยง" : "risk"} {fund.risk_level}
                                    </span>
                                  </div>
                                  {fund.fund_name && <span className="text-[10px] text-slate-500 leading-snug">{fund.fund_name}</span>}
                                  <div className="flex items-center justify-between text-[11px] mt-0.5">
                                    <span className="font-mono text-slate-300 font-semibold">{formatTHB(fund.amount_thb)}</span>
                                    <span className="font-mono text-slate-400">{fund.allocation_percentage}%</span>
                                  </div>
                                  {fund.esg_rating && fund.esg_rating !== "N/A" && (
                                    <span className="inline-block w-fit px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 font-bold font-mono">ESG {fund.esg_rating}</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {result.explanation?.overall_explanation && (
                      <div className="mt-2 p-4 bg-slate-950/30 border border-white/5 rounded-lg">
                        <p className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">{lang === "th" ? "กลยุทธ์การจัดพอร์ตโดยที่ปรึกษา" : "Advisor Construction Strategy"}:</p>
                        <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">{result.explanation.overall_explanation}</p>
                      </div>
                    )}
                  </div>
                )}

                {/* 6. SEC Compliance & Audit safeguards */}
                {result.compliance && (
                  <div className="glass-panel p-6 border-white/5 flex flex-col gap-4">
                    <div className="flex items-center justify-between border-b border-white/5 pb-3">
                      <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">{lang === "th" ? "รายงานการตรวจสอบกำกับ SEC" : "SEC Compliance Safeguard Report"}</h3>
                      <span className="text-xs text-slate-400">Compliance Audit Agent</span>
                    </div>

                    <div className="flex items-start gap-4">
                      {result.compliance.approved ? (
                        <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20 shadow-lg shadow-emerald-500/5">
                          <ShieldCheck className="h-8 w-8" />
                        </div>
                      ) : (
                        <div className="p-3 bg-red-500/10 text-red-400 rounded-full border border-red-500/20 shadow-lg shadow-red-500/5">
                          <ShieldAlert className="h-8 w-8 animate-pulse" />
                        </div>
                      )}

                      <div className="flex-1 flex flex-col gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold">Status:</span>
                          <span className={`text-sm font-bold tracking-wider ${result.compliance.approved ? 'text-emerald-400' : 'text-red-400'}`}>
                            {result.compliance.approved ? 'PASSED & COMPLIANT' : 'VIOLATION DETECTED'}
                          </span>
                        </div>
                        
                        <p className="text-xs text-slate-300 leading-relaxed font-mono">
                          {result.compliance.approved 
                            ? "All recommendations comply with SEC Thailand regulations. No return guarantee claims detected."
                            : `Compliance checks flagged ${result.compliance.issues?.length ?? 0} critical violation(s). Core requirements failed.`
                          }
                        </p>
                      </div>
                    </div>

                    {/* Issues List */}
                    {result.compliance.issues?.length > 0 && (
                      <div className="mt-2 flex flex-col gap-2">
                        <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Compliance Findings</span>
                        <div className="flex flex-col gap-1.5">
                          {result.compliance.issues.map((iss: any, idx: number) => {
                            const crit = iss.severity === "critical";
                            return (
                              <div key={idx} className={`p-2.5 rounded-md text-xs flex items-start gap-2 border ${crit ? "bg-red-500/5 border-red-500/15 text-red-300" : "bg-amber-500/5 border-amber-500/15 text-amber-300"}`}>
                                <span className={`font-bold shrink-0 uppercase text-[10px] mt-0.5 ${crit ? "text-red-400" : "text-amber-400"}`}>{iss.severity}</span>
                                <span>{iss.description}{iss.route_back_to ? <span className="text-slate-500"> · → {friendlyAgent(iss.route_back_to, lang)}</span> : null}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Explainable-AI Decision Timeline */}
                {audit && (
                  <div className="glass-panel p-6 border-white/5 flex flex-col gap-4">
                    <div className="flex items-center justify-between border-b border-white/5 pb-3">
                      <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase font-outfit">{lang === "th" ? "ไทม์ไลน์การตัดสินใจ (อธิบายได้)" : "Explainable Decision Timeline"}</h3>
                      <Clock className="h-4 w-4 text-slate-400" />
                    </div>

                    <div className="flex flex-col gap-5 mt-1">
                      {buildDecisionTimeline(result, audit.score).map((phase, idx) => (
                        <div key={idx} className="flex gap-3">
                          <div className="flex flex-col items-center">
                            <div className="h-6 w-6 bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0">
                              {idx + 1}
                            </div>
                            <div className="flex-1 w-px bg-white/10 mt-1" />
                          </div>
                          <div className="flex-1 pb-1">
                            <p className="text-sm font-semibold text-slate-200">
                              <span className="text-indigo-400">PHASE {idx + 1}:</span> {phase.title}
                            </p>
                            <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-3">
                              <div>
                                <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-1">Evidence</p>
                                <ul className="flex flex-col gap-1">
                                  {phase.evidence.map((e, i) => (
                                    <li key={i} className="text-xs text-slate-400 flex gap-1.5"><span className="text-slate-600">•</span><span>{e}</span></li>
                                  ))}
                                </ul>
                              </div>
                              <div>
                                <p className="text-[10px] uppercase font-bold text-emerald-500/70 tracking-wider mb-1">Conclusion</p>
                                <ul className="flex flex-col gap-1">
                                  {phase.conclusion.map((e, i) => (
                                    <li key={i} className="text-xs text-emerald-300/90 flex gap-1.5"><span className="text-emerald-500/60">→</span><span>{e}</span></li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Raw execution log (collapsible) */}
                    {result.trace && (
                      <div className="border-t border-white/5 pt-3">
                        <button
                          onClick={() => setRawLogOpen(!rawLogOpen)}
                          className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 hover:text-slate-300 transition-colors"
                        >
                          {rawLogOpen ? "Hide" : "Show"} raw execution log ({result.trace.length} steps)
                          <ChevronDown className={`h-3.5 w-3.5 transition-transform ${rawLogOpen ? "rotate-180" : ""}`} />
                        </button>
                        {rawLogOpen && (
                          <div className="flex flex-col gap-1.5 mt-3">
                            {result.trace.map((step: string, idx: number) => (
                              <div key={idx} className="text-[11px] text-slate-400 font-mono border-l border-white/5 pl-3 py-0.5">
                                {idx + 1}. {step}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

              </div>
            )}
          </div>
        </div>
        )}

        {/* ===== CHAT VIEW ===== */}
        {view === "chat" && (
        <div className="max-w-6xl mx-auto">
          {!result?.session_id ? (
            <div className="glass-panel p-16 flex flex-col items-center justify-center text-center gap-4 border-dashed border-white/10 min-h-[400px]">
              <MessageCircle className="h-8 w-8 text-indigo-400" />
              <div>
                <h3 className="text-lg font-semibold tracking-tight text-slate-300">{tr(lang, "noSessionTitle")}</h3>
                <p className="text-sm text-slate-400 max-w-sm mt-1 mx-auto">{tr(lang, "noSessionBody")}</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div className="lg:col-span-7 glass-panel p-6 border-white/5 flex flex-col gap-4">
              <div className="flex items-center justify-between border-b border-white/5 pb-3">
                <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase font-outfit">{lang === "th" ? "ถามที่ปรึกษา AI" : "Ask the AI Advisor"}</h3>
                <MessageCircle className="h-4 w-4 text-slate-400" />
              </div>

              <div className="flex flex-col gap-3 max-h-[60vh] overflow-y-auto pr-1">
                {chatMessages.length === 0 && (
                  <p className="text-xs text-slate-500 leading-relaxed">
                    ถามคำถามเกี่ยวกับผลการวิเคราะห์นี้ได้เลย เช่น &quot;ประหยัดภาษีได้เท่าไหร่?&quot; หรือ &quot;ทำไมแนะนำกองทุนนี้?&quot;
                    <br />
                    <span className="text-slate-600">คำตอบอ้างอิงจากผลของระบบเท่านั้น และไม่ใช่คำแนะนำที่ผ่านการรับรองจนกว่าที่ปรึกษาจะตรวจสอบ</span>
                  </p>
                )}
                {chatMessages.map((m, idx) => (
                  <div key={idx} className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
                    <div className={`max-w-[85%] rounded-lg px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap ${
                      m.role === "user"
                        ? "bg-indigo-500/15 text-indigo-100 border border-indigo-500/20"
                        : "bg-white/5 text-slate-200 border border-white/10"
                    }`}>
                      {m.text}
                    </div>
                    {m.action?.type === "reanalyze_form" && (
                      <WhatIfCTA
                        label={m.action.label}
                        initialAmount={m.action.prefill?.investment_amount}
                        disabled={loading}
                        onRun={handleWhatIfReanalyze}
                      />
                    )}
                    {m.action?.type === "escalate_to_advisor" && (
                      <div className="mt-2 max-w-[85%] rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 flex flex-col gap-1">
                        <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-amber-300/80 font-outfit">
                          <ShieldAlert className="h-3 w-3" /> escalate_to_advisor
                        </div>
                        <div className="text-xs text-slate-200">{m.action.label}</div>
                        {m.action.contact_method && (
                          <div className="text-[11px] text-amber-200/80 break-all">{m.action.contact_method}</div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
                {chatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-white/5 text-slate-400 border border-white/10 rounded-lg px-3 py-2 text-xs flex items-center gap-2">
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" /> กำลังคิด...
                    </div>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2 border-t border-white/5 pt-3">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !chatLoading) handleSendChat(); }}
                  placeholder="พิมพ์คำถามของคุณ..."
                  disabled={chatLoading}
                  className="flex-1 bg-white/5 border border-white/10 rounded-md px-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/40 disabled:opacity-50"
                />
                <button
                  onClick={handleSendChat}
                  disabled={chatLoading || !chatInput.trim()}
                  className="p-2 bg-indigo-500/15 text-indigo-300 border border-indigo-500/20 rounded-md hover:bg-indigo-500/25 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Right: live summary so the client doesn't need to go back to Results */}
            <div className="lg:col-span-5 flex flex-col gap-4">
              <div className="glass-panel p-4 border-white/5 flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">{lang === "th" ? "การกำกับ (SEC)" : "Compliance"}</span>
                <span className={`text-sm font-bold ${result.compliance ? (result.compliance.approved ? "text-emerald-400" : "text-red-400") : "text-amber-400"}`}>
                  {result.compliance ? (result.compliance.approved ? (lang === "th" ? "ผ่าน" : "Approved") : (lang === "th" ? "ไม่ผ่าน" : "Rejected")) : (lang === "th" ? "รอตรวจ" : "Pending")}
                </span>
              </div>

              {result.tax_result && (
                <div className="glass-panel p-4 border-white/5 flex flex-col gap-2">
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">{lang === "th" ? "สรุปภาษี" : "Tax Summary"}</span>
                  <div className="flex justify-between text-xs"><span className="text-slate-400">{lang === "th" ? "ก่อนปรับ" : "Before"}</span><span className="font-mono text-slate-300">{formatTHB(result.tax_result.tax_before)}</span></div>
                  <div className="flex justify-between text-xs"><span className="text-slate-400">{lang === "th" ? "หลังปรับ" : "After"}</span><span className="font-mono text-slate-300">{formatTHB(result.tax_result.tax_after)}</span></div>
                  <div className="flex justify-between text-sm border-t border-white/5 pt-2"><span className="text-emerald-400 font-semibold">{lang === "th" ? "ประหยัด" : "Saved"}</span><span className="font-mono font-bold text-emerald-400">{formatTHB(result.tax_result.saving)}</span></div>
                </div>
              )}

              {result.recommendation?.recommended_funds?.length > 0 && (
                <div className="glass-panel p-4 border-white/5 flex flex-col gap-2">
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">{lang === "th" ? "กองทุนที่แนะนำ" : "Recommended Funds"}</span>
                  {result.recommendation.recommended_funds.map((f: any, i: number) => (
                    <div key={i} className="flex justify-between items-center text-xs border-b border-white/5 last:border-0 pb-1.5 last:pb-0">
                      <span className="text-slate-300"><span className="font-semibold">{f.fund_code}</span> <span className="text-slate-500">· {f.fund_type}</span></span>
                      <span className="font-mono text-slate-400">{formatTHB(f.amount_thb)}</span>
                    </div>
                  ))}
                </div>
              )}

              <div className="glass-panel p-4 border-white/5 grid grid-cols-2 gap-3">
                <div className="flex flex-col"><span className="text-[10px] uppercase font-bold text-slate-500">{lang === "th" ? "อายุ" : "Age"}</span><span className="text-sm text-slate-200">{dash(result.typhoon_result?.entities?.age)}</span></div>
                <div className="flex flex-col"><span className="text-[10px] uppercase font-bold text-slate-500">{lang === "th" ? "ความเสี่ยง" : "Risk"}</span><span className="text-sm text-indigo-400">{dash(result.typhoon_result?.entities?.risk_profile)}</span></div>
                <div className="flex flex-col col-span-2"><span className="text-[10px] uppercase font-bold text-slate-500">{lang === "th" ? "เป้าหมาย" : "Goal"}</span><span className="text-sm text-emerald-400">{dash(result.typhoon_result?.entities?.goal)}</span></div>
              </div>

              <button
                onClick={() => router.push("/results")}
                className="text-center text-xs text-indigo-300 hover:text-indigo-200 py-2"
              >
                {lang === "th" ? "ดูผลแบบเต็ม →" : "View full results →"}
              </button>
            </div>
            </div>
          )}
        </div>
        )}
      </main>
    </div>
  );
}
