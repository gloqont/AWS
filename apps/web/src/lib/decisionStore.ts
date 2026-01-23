export type TaxCountry =
  | "United States"
  | "India"
  | "United Kingdom"
  | "Europe (Generic)"
  | "Other";

export type LastDecision = {
  decisionText: string;
  expectedBeforeTaxPct: number; // e.g. -1.2 means -1.2%
  totalValue: number;          // portfolio total $ value
  taxCountry: TaxCountry;
  createdAt: string;           // ISO
};

const KEY = "advisor_last_decision_v1";

export function saveLastDecision(d: LastDecision) {
  localStorage.setItem(KEY, JSON.stringify(d));
}

export function loadLastDecision(): LastDecision | null {
  const raw = localStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as LastDecision;
  } catch {
    return null;
  }
}

export function clearLastDecision() {
  localStorage.removeItem(KEY);
}