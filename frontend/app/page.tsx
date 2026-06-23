"use client";

import React, { useState } from 'react';
import { 
  User, 
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
  Gauge
} from 'lucide-react';
import { ReactFlow, Background, Controls } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// Backend base URL. Set NEXT_PUBLIC_API_URL in the deployment environment
// (e.g. the Render backend URL); falls back to localhost for local dev.
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const PRESETS = [
  {
    name: "Client A (Salary, Compliant)",
    text: `เงินเดือนประมาณแสนห้า\nโบนัสปีละ 4 เดือน\nซื้อ RMF บ้างนิดหน่อย\nมีประกันชีวิตอยู่แล้ว\nอยากลดภาษีเพิ่ม\nความเสี่ยงปานกลาง เน้นพอร์ตแบบสมดุล`
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

// Uncertainty-Quantification (UQ) audit: a transparent confidence score for the
// whole advisory run, derived from signals the pipeline already produced.
function computeAudit(result: any) {
  const t = result?.typhoon_result;
  const conf = Math.round((t?.confidence ?? 0) * 100);
  const missing = t?.missing_information?.length ?? 0;
  const completeness = Math.max(0, 100 - missing * 12);
  const comp = result?.compliance;
  const complianceScore = comp
    ? (comp.status === "approved" ? 100 : Math.max(30, 100 - (comp.violations?.length ?? 0) * 30))
    : 70;
  const funds = result?.recommendation?.recommended_funds?.length ?? 0;
  const fit = funds > 0 ? 100 : 50;
  const factors = [
    { label: "NLP Extraction Confidence", value: conf, weight: 0.30, note: "Typhoon interpreter certainty" },
    { label: "Profile Completeness", value: completeness, weight: 0.30, note: missing ? `${missing} field(s) missing` : "All key fields present" },
    { label: "Compliance Integrity", value: complianceScore, weight: 0.25, note: comp ? (comp.status === "approved" ? "No violations" : `${comp.violations?.length ?? 0} violation(s)`) : "Pending advisor approval" },
    { label: "Recommendation Coverage", value: fit, weight: 0.15, note: funds ? `${funds} fund(s) matched` : "No funds matched" },
  ];
  const score = Math.round(factors.reduce((s, f) => s + f.value * f.weight, 0));
  return { score, factors };
}

export default function Dashboard() {
  const [inputText, setInputText] = useState(PRESETS[0].text);
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [error, setError] = useState<string | null>(null);
  
  // Results & Graph State
  const [result, setResult] = useState<any>(null);
  const [flowGraph, setFlowGraph] = useState<any>(null);

  // File upload state
  const [fileLoading, setFileLoading] = useState(false);
  const [fileInfo, setFileInfo] = useState<string | null>(null);

  // Which audit card is expanded ('compliance' | 'uq' | null)
  const [auditOpen, setAuditOpen] = useState<null | "compliance" | "uq">(null);

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

  const fetchFlowGraph = async (sid: string) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/session/${sid}`);
      if (res.ok) {
        const data = await res.json();
        setFlowGraph(data.flow_graph);
      }
    } catch (err) {
      console.error("Failed to fetch session flow graph", err);
    }
  };

  const handleRunWorkflow = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setFlowGraph(null);
    setStatusText("Initializing LangGraph Orchestrator...");
    
    try {
      setStatusText("Agent 1: Interpreting Thai financial conversation (Typhoon)...");
      const response = await fetch(`${API_URL}/api/v1/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ raw_input_text: inputText })
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
      if (data.session_id) {
        await fetchFlowGraph(data.session_id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to connect to backend server. Make sure FastAPI is running on port 8000.");
    } finally {
      setLoading(false);
      setStatusText("");
    }
  };

  const handleApprove = async () => {
    if (!result || !result.session_id) return;
    setLoading(true);
    setError(null);
    setStatusText("Resuming workflow and running compliance checks...");
    
    try {
      const response = await fetch(`${API_URL}/api/v1/recommend`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ session_id: result.session_id })
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
      if (data.session_id) {
        await fetchFlowGraph(data.session_id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to approve recommendation.");
    } finally {
      setLoading(false);
      setStatusText("");
    }
  };

  // Helper to format currency
  const formatTHB = (val?: number) => {
    if (val === undefined || val === null) return "฿0.00";
    return new Intl.NumberFormat('th-TH', { style: 'currency', currency: 'THB' }).format(val);
  };

  const audit = result ? computeAudit(result) : null;

  return (
    <div className="min-h-screen pb-16 bg-[#080d16] text-[#f3f4f6] font-sans selection:bg-indigo-600 selection:text-white">
      {/* Background Decorative Blobs */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-900/10 rounded-full blur-3xl pointer-events-none animate-pulse-slow"></div>
      <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-emerald-900/10 rounded-full blur-3xl pointer-events-none animate-pulse-slow" style={{ animationDelay: '2s' }}></div>

      {/* Header */}
      <header className="border-b border-white/5 bg-slate-950/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-gradient-to-tr from-indigo-600 to-indigo-400 rounded-lg shadow-lg shadow-indigo-500/20">
              <Activity className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-lg tracking-tight">Chief Wealth Intelligence Officer</h1>
              <p className="text-xs text-slate-400">9-Agent Production Architecture (LangGraph & Typhoon NLP)</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Active Connection
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left Column: Input Panel */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            <div className="glass-panel p-6 glow-indigo flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold tracking-wider text-indigo-400 uppercase font-outfit">Client Transcription (Thai)</h2>
                <Coins className="h-4 w-4 text-slate-400" />
              </div>
              <p className="text-xs text-slate-400">
                Paste client descriptions or conversations. The Typhoon model translates and extracts details before reasoning.
              </p>

              {/* Presets */}
              <div className="flex flex-col gap-2 mt-2">
                <span className="text-[10px] uppercase font-bold text-slate-500">Intake Presets</span>
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
                <span className="text-[10px] uppercase font-bold text-slate-500">Or upload a document</span>
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
                onClick={handleRunWorkflow}
                disabled={loading}
                className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium text-sm rounded-lg transition-colors flex items-center justify-center gap-2 mt-2 shadow-lg shadow-indigo-600/20"
              >
                {loading ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>Processing Agents...</span>
                  </>
                ) : (
                  <>
                    <span>Run Orchestrator Loop</span>
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
              <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">System Status</h3>
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

          {/* Right Column: Results & Analytics */}
          <div className="lg:col-span-8 flex flex-col gap-6">
            
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
                
                {/* Advisor Action Banner (Human in the Loop Checkpoint) */}
                {result.status === "awaiting_review" && (
                  <div className="p-6 bg-indigo-950/40 border border-indigo-500/30 rounded-xl glow-indigo flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <div className="p-2.5 bg-indigo-500/20 text-indigo-300 rounded-lg shrink-0 mt-0.5">
                        <User className="h-5 w-5 animate-pulse" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-base text-indigo-200">Advisor Action Required</h3>
                        <p className="text-xs text-slate-300 mt-1 max-w-xl">
                          The 9-agent workflow has paused at the Human Review checkpoint. Please review the Typhoon interpretation, tax calculations, and proposed recommendations below. Click Approve to finalize compliance audits.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 w-full md:w-auto">
                      <button
                        onClick={handleApprove}
                        disabled={loading}
                        className="flex-1 md:flex-initial px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-indigo-600/20 flex items-center justify-center gap-1.5"
                      >
                        {loading ? <RefreshCw className="h-3 w-3 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                        Approve & Submit Compliance
                      </button>
                      <button
                        onClick={() => {
                          setResult(null);
                          setError(null);
                        }}
                        className="flex-1 md:flex-initial px-4 py-2.5 bg-slate-900/60 hover:bg-slate-800/40 border border-white/5 text-slate-300 text-xs font-semibold rounded-lg"
                      >
                        Reset
                      </button>
                    </div>
                  </div>
                )}

                {/* 1. Client Info Summary */}
                <div className="glass-panel p-6 border-white/5 grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Client Age</span>
                    <span className="text-lg font-semibold text-slate-200">{result.client_data?.age ?? "N/A"} Years Old</span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Assessable Income</span>
                    <span className="text-lg font-semibold text-slate-200">
                      {result.client_data 
                        ? formatTHB((result.client_data.monthly_income * 12) + (result.client_data.monthly_income * result.client_data.bonus_months))
                        : "N/A"
                      }
                    </span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Risk Profile</span>
                    <span className="text-lg font-semibold text-indigo-400">{result.client_data?.risk_profile ?? "N/A"}</span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Financial Goal</span>
                    <span className="text-lg font-semibold text-emerald-400">{result.client_data?.goal ?? "N/A"}</span>
                  </div>
                </div>

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
                            result.compliance.status === "approved" ? (
                              <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg border border-emerald-500/20"><ShieldCheck className="h-6 w-6" /></div>
                            ) : (
                              <div className="p-2 bg-red-500/10 text-red-400 rounded-lg border border-red-500/20"><ShieldAlert className="h-6 w-6" /></div>
                            )
                          ) : (
                            <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg border border-amber-500/20"><Clock className="h-6 w-6" /></div>
                          )}
                          <div>
                            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Compliance</p>
                            <p className={`text-lg font-bold ${result.compliance ? (result.compliance.status === "approved" ? "text-emerald-400" : "text-red-400") : "text-amber-400"}`}>
                              {result.compliance ? (result.compliance.status === "approved" ? "Compliant" : "Violation") : "Pending"}
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
                            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">UQ Audit · Confidence</p>
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
                          <p className="text-xs text-amber-300">The SEC audit runs after you approve the recommendation. Click “Approve &amp; Submit Compliance” above.</p>
                        ) : result.compliance.violations?.length > 0 ? (
                          <div className="flex flex-col gap-1.5">
                            {result.compliance.violations.map((v: string, i: number) => (
                              <div key={i} className="p-2.5 bg-red-500/5 border border-red-500/15 rounded-md text-xs text-red-300 flex items-start gap-2">
                                <span className="text-red-400 font-bold shrink-0">•</span><span>{v}</span>
                              </div>
                            ))}
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
                        <h3 className="text-sm font-semibold tracking-wider text-indigo-400 uppercase font-outfit">Typhoon Thai NLP Interpreter</h3>
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
                        <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Extracted Values Table</span>
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
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                    
                    {/* Tax numbers */}
                    <div className="md:col-span-5 glass-panel p-6 border-white/5 flex flex-col justify-between gap-4">
                      <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">Tax Optimization Results</h3>
                      
                      <div className="flex flex-col gap-3">
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-slate-400">Tax Before Optimization:</span>
                          <span className="font-semibold text-slate-300 font-mono">{formatTHB(result.tax_result.tax_before)}</span>
                        </div>
                        <div className="flex justify-between items-center text-sm border-b border-white/5 pb-3">
                          <span className="text-slate-400">Tax After Optimization:</span>
                          <span className="font-semibold text-slate-300 font-mono">{formatTHB(result.tax_result.tax_after)}</span>
                        </div>
                        <div className="flex justify-between items-center py-2">
                          <span className="text-emerald-400 font-semibold text-sm">Tax Saved:</span>
                          <span className="font-bold text-lg text-emerald-400 font-mono">{formatTHB(result.tax_result.saving)}</span>
                        </div>
                      </div>

                      <div className="p-3 bg-emerald-500/5 border border-emerald-500/10 rounded-lg flex items-start gap-2.5">
                        <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                        <p className="text-[11px] text-emerald-300 leading-relaxed">
                          Deterministic calculations applied. Tax liability minimized from {formatTHB(result.tax_result.tax_before)} to {formatTHB(result.tax_result.tax_after)}.
                        </p>
                      </div>
                    </div>

                    {/* SVG Chart Comparison */}
                    <div className="md:col-span-7 glass-panel p-6 border-white/5 flex flex-col gap-4">
                      <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">Visualized Comparison (THB)</h3>
                      
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
                )}

                {/* 4. Detailed Optimizations Investments */}
                {result.tax_result?.detailed_calculations?.optimization_purchases && (
                  <div className="glass-panel p-6 border-white/5 flex flex-col gap-4">
                    <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">Required Investments to achieve tax savings</h3>
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

                {/* 5. Portfolio Fund Recommendations */}
                {result.recommendation && (
                  <div className="glass-panel p-6 border-white/5 flex flex-col gap-4">
                    <div className="flex items-center justify-between border-b border-white/5 pb-3">
                      <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">Recommended Portfolio Allocation</h3>
                      <span className="text-xs text-slate-400">Based on Risk profile & Goals</span>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm border-collapse">
                        <thead>
                          <tr className="border-b border-white/5 text-slate-500">
                            <th className="py-2.5 font-semibold text-xs uppercase">Fund Code</th>
                            <th className="py-2.5 font-semibold text-xs uppercase">Type</th>
                            <th className="py-2.5 font-semibold text-xs uppercase text-center">Risk</th>
                            <th className="py-2.5 font-semibold text-xs uppercase text-center">ESG</th>
                            <th className="py-2.5 font-semibold text-xs uppercase text-right">Amount (THB)</th>
                            <th className="py-2.5 font-semibold text-xs uppercase text-right">Weight</th>
                          </tr>
                        </thead>
                        <tbody>
                          {result.recommendation.recommended_funds?.map((fund: any, idx: number) => (
                            <tr key={idx} className="border-b border-white/5 text-slate-300 hover:bg-slate-900/10">
                              <td className="py-3 font-semibold">
                                <div>{fund.fund_code}</div>
                                <div className="text-[10px] text-slate-500 font-normal">{fund.fund_name}</div>
                              </td>
                              <td className="py-3 text-xs">{fund.fund_type}</td>
                              <td className="py-3 text-center">
                                <span className="inline-block px-1.5 py-0.5 rounded text-[11px] bg-indigo-500/10 text-indigo-400 font-medium font-mono">
                                  {fund.risk_level}
                                </span>
                              </td>
                              <td className="py-3 text-center">
                                {fund.esg_rating && fund.esg_rating !== "N/A" ? (
                                  <span className="inline-block px-1.5 py-0.5 rounded text-[11px] bg-emerald-500/10 text-emerald-400 font-bold font-mono">
                                    {fund.esg_rating}
                                  </span>
                                ) : (
                                  <span className="text-slate-600">-</span>
                                )}
                              </td>
                              <td className="py-3 text-right font-mono font-semibold">{formatTHB(fund.amount_thb)}</td>
                              <td className="py-3 text-right font-mono font-semibold">{fund.allocation_percentage}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {result.explanation?.overall_explanation && (
                      <div className="mt-4 p-4 bg-slate-950/30 border border-white/5 rounded-lg">
                        <p className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Advisor Construction Strategy:</p>
                        <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">{result.explanation.overall_explanation}</p>
                      </div>
                    )}
                  </div>
                )}

                {/* 6. SEC Compliance & Audit safeguards */}
                {result.compliance && (
                  <div className="glass-panel p-6 border-white/5 flex flex-col gap-4">
                    <div className="flex items-center justify-between border-b border-white/5 pb-3">
                      <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">SEC Compliance Safeguard Report</h3>
                      <span className="text-xs text-slate-400">Compliance Audit Agent</span>
                    </div>

                    <div className="flex items-start gap-4">
                      {result.compliance.status === "approved" ? (
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
                          <span className={`text-sm font-bold tracking-wider ${result.compliance.status === "approved" ? 'text-emerald-400' : 'text-red-400'}`}>
                            {result.compliance.status === "approved" ? 'PASSED & COMPLIANT' : 'VIOLATION DETECTED'}
                          </span>
                        </div>
                        
                        <p className="text-xs text-slate-300 leading-relaxed font-mono">
                          {result.compliance.status === "approved" 
                            ? "All recommendations comply with SEC Thailand regulations. No return guarantee claims detected."
                            : `Compliance checks flagged ${result.compliance.violations?.length ?? 0} critical violation(s). Core requirements failed.`
                          }
                        </p>
                      </div>
                    </div>

                    {/* Violations List */}
                    {result.compliance.violations?.length > 0 && (
                      <div className="mt-2 flex flex-col gap-2">
                        <span className="text-[10px] uppercase font-bold text-red-400 tracking-wider">Critical Violations</span>
                        <div className="flex flex-col gap-1.5">
                          {result.compliance.violations.map((v: string, idx: number) => (
                            <div key={idx} className="p-2.5 bg-red-500/5 border border-red-500/15 rounded-md text-xs text-red-300 flex items-start gap-2 font-mono">
                              <span className="text-red-400 font-bold shrink-0">•</span>
                              <span>{v}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 7. React Flow / LangGraph Workflow Map */}
                {result.session_id && flowGraph && (
                  <div className="glass-panel p-6 border-white/5 flex flex-col gap-4">
                    <div className="flex items-center justify-between border-b border-white/5 pb-3">
                      <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">LangGraph Active Path Visualizer</h3>
                      <FileSpreadsheet className="h-4 w-4 text-slate-400" />
                    </div>

                    <div className="h-80 border border-white/5 rounded-lg overflow-hidden bg-slate-950/40 relative">
                      <ReactFlow
                        nodes={flowGraph.nodes}
                        edges={flowGraph.edges}
                        fitView
                        nodesConnectable={false}
                        nodesDraggable={false}
                        zoomOnScroll={false}
                        zoomOnPinch={false}
                        zoomOnDoubleClick={false}
                        panOnDrag={false}
                        panOnScroll={false}
                        preventScrolling={true}
                      >
                        <Background color="#1e293b" gap={16} size={1} />
                        <Controls showInteractive={false} className="opacity-50" />
                      </ReactFlow>
                    </div>
                  </div>
                )}

                {/* 8. Explainability & Audit Trail Timeline */}
                {result.trace && (
                  <div className="glass-panel p-6 border-white/5 flex flex-col gap-4">
                    <div className="flex items-center justify-between border-b border-white/5 pb-3">
                      <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase font-outfit">LangGraph Execution Timeline (Audit Trail)</h3>
                      <Clock className="h-4 w-4 text-slate-400" />
                    </div>

                    <div className="flex flex-col gap-4 mt-2">
                      {result.trace.map((step: string, idx: number) => (
                        <div key={idx} className="flex gap-3 text-xs leading-relaxed items-start">
                          <div className="h-5 w-5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
                            {idx + 1}
                          </div>
                          <div className="flex-1 text-slate-300 font-mono border-l border-white/5 pl-3 py-0.5">
                            {step}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            )}
          </div>
          
        </div>
      </main>
    </div>
  );
}
