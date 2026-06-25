// Shared constants + pure helpers used by both the session context (for
// re-analysis overrides) and the DashboardShell (for rendering). Kept in one
// place so chat/intake/results never diverge on field definitions.

// Backend base URL. Set NEXT_PUBLIC_API_URL in the deployment environment
// (e.g. the Render backend URL); falls back to localhost for local dev.
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const PRESETS = [
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
export const PROFILE_FIELDS: { key: string; label: string; penalty: number; placeholder: string; type: string }[] = [
  { key: "monthly_income", label: "Monthly Income (THB)", penalty: 10, placeholder: "e.g. 150000", type: "number" },
  { key: "age", label: "Age", penalty: 5, placeholder: "e.g. 35", type: "number" },
  { key: "risk_profile", label: "Risk Preference", penalty: 5, placeholder: "Conservative / Moderate / Aggressive", type: "text" },
  { key: "employment_type", label: "Employment Type", penalty: 5, placeholder: "salary / freelance", type: "text" },
  { key: "goal", label: "Financial Goal", penalty: 4, placeholder: "e.g. tax optimization", type: "text" },
  { key: "ssf", label: "SSF Investment (THB/year)", penalty: 3, placeholder: "e.g. 60000", type: "number" },
  { key: "rmf", label: "RMF Investment (THB/year)", penalty: 3, placeholder: "e.g. 30000", type: "number" },
  { key: "life_insurance", label: "Life Insurance (THB/year)", penalty: 3, placeholder: "e.g. 25000", type: "number" },
];

// Tracked profile fields the client did NOT provide (from extracted entities).
export function getMissingFields(result: any) {
  const ent = result?.typhoon_result?.entities || {};
  return PROFILE_FIELDS.filter((f) => {
    if (f.key === "monthly_income") return ent.monthly_income == null && ent.annual_income == null;
    return ent[f.key] === null || ent[f.key] === undefined;
  });
}

// Whether the session has enough data to render the full Results dashboard
// (tax/recommendation sections). When false, Results renders ONLY the
// interpreter panel + a banner — never code that assumes tax_result exists.
export function isSessionComplete(result: any): boolean {
  if (!result) return false;
  if (result.typhoon_result?.ambiguous) return false;
  if (result.status === "needs_clarification" || result.status === "needs_review") return false;
  // Primary signal: the pipeline actually produced downstream artifacts.
  return Boolean(result.tax_result || result.recommendation);
}
