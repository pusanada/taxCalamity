// Static-UI-label i18n scaffold. Covers nav + page-level chrome now; body
// labels are translated incrementally. IMPORTANT: this ONLY swaps static UI
// text — it must never translate LLM-generated content (chat replies, fund
// explanations, normalized_thai, the Thai disclaimer), because deterministic
// checks string-match Thai directly (_THAI_DISCLAIMER in agents.py, the Thai
// patterns in pii_masking.py). Translating model output would break them.

export type Lang = "th" | "en";

export const LANGS: { code: Lang; label: string }[] = [
  { code: "th", label: "ไทย" },
  { code: "en", label: "EN" },
];

const DICT: Record<Lang, Record<string, string>> = {
  th: {
    appTitle: "Chief Wealth Intelligence Officer",
    appSubtitle: "สถาปัตยกรรม 9 Agent (LangGraph & Typhoon NLP)",
    activeConnection: "เชื่อมต่อแล้ว",
    navIntake: "กรอกข้อมูล",
    navResults: "ผลลัพธ์",
    navChat: "แชท",
    chatDisabledTip: "วิเคราะห์ข้อมูลก่อนเริ่มแชท",
    goToResults: "ไปหน้าผลลัพธ์",
    intakeHeader: "ข้อมูลลูกค้า (ภาษาไทย)",
    resultsHeader: "ผลการวิเคราะห์",
    incompleteTitle: "ข้อมูลยังไม่ครบ",
    incompleteBody: "กลับไปกรอกข้อมูลเพิ่มที่หน้า “กรอกข้อมูล” หรือดูสิ่งที่ระบบสกัดได้แล้วด้านล่าง คุณยังเริ่มแชทถามเพิ่มได้",
    noSessionTitle: "ยังไม่มี session",
    noSessionBody: "วิเคราะห์ข้อมูลลูกค้าที่หน้า “กรอกข้อมูล” ก่อน แล้วจึงกลับมาที่หน้านี้",
  },
  en: {
    appTitle: "Chief Wealth Intelligence Officer",
    appSubtitle: "9-Agent Production Architecture (LangGraph & Typhoon NLP)",
    activeConnection: "Active Connection",
    navIntake: "Intake",
    navResults: "Results",
    navChat: "Chat",
    chatDisabledTip: "Analyze a profile before chatting",
    goToResults: "Go to results",
    intakeHeader: "Client Transcription (Thai)",
    resultsHeader: "Analysis Results",
    incompleteTitle: "Profile incomplete",
    incompleteBody: "Go back to Intake to add details, or review what the system already extracted below. You can still start a chat.",
    noSessionTitle: "No active session",
    noSessionBody: "Analyze a client profile on the Intake page first, then return here.",
  },
};

export function tr(lang: Lang, key: string): string {
  return DICT[lang]?.[key] ?? DICT.en[key] ?? key;
}
