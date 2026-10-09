// Shapes of the files the web app reads. Pack config (theme.json,
// customers.json) is written by hand per pack; scenes.json is written by the
// pipeline's render step (pipeline/render.py).

export interface Theme {
  brand: {
    name: string;
    short_name: string;
    wordmark: string;
    mark: string; // name of a built-in SVG mark, e.g. "leaf"
    tagline: string;
    fictional: boolean;
  };
  color: Record<string, string>; // token name -> hex, e.g. primary -> "#0E4D4A"
  font: { heading: string; body: string }; // Google Fonts family names
  shape: { radius: string };
  motion: { style: string; scene_transition_ms: number };
  voice: { lang: string; rate: number; pitch: number; preferred_voices: string[] };
  tone: string;
  contrast_pairs: { fg: string; bg: string; min: number }[];
}

/** What the app knows about a customer. Deliberately excludes the document path. */
export interface Customer {
  id: string;
  preferred_name: string;
  persona: string;
  prefs: { captions: boolean; speech_rate: number };
}

export interface Pack {
  name: string; // folder name under packs/, e.g. "mortgage"
  theme: Theme;
  customers: Customer[];
}

export type Tone = "info" | "important" | "danger";

// One interface per visual type. The `type` field tells them apart, so
// TypeScript knows which other fields exist (a "discriminated union").
export interface TitleVisual {
  type: "title";
  heading: string;
  subheading?: string;
}

export interface StatVisual {
  type: "stat";
  stats: { label: string; value: string }[];
  meter?: { label: string; value: number; max: number; unit: string };
}

export interface ComparisonVisual {
  type: "comparison";
  before: { label: string; value: string; caption?: string };
  after: { label: string; value: string; caption?: string };
  delta: string;
}

export interface TimelineVisual {
  type: "timeline";
  tone?: Tone;
  items: { time: string; label: string }[];
}

export interface TableVisual {
  type: "table";
  columns: string[];
  rows: string[][];
  footnote?: string;
}

export interface ChecklistVisual {
  type: "checklist";
  items: string[];
}

export interface AlertVisual {
  type: "alert";
  tone: Tone;
  heading: string;
  body?: string;
  items?: string[];
}

export interface ContactVisual {
  type: "contact";
  phone: string;
  secondary_phone?: string;
  reference?: string;
  hours?: string;
}

export type Visual =
  | TitleVisual
  | StatVisual
  | ComparisonVisual
  | TimelineVisual
  | TableVisual
  | ChecklistVisual
  | AlertVisual
  | ContactVisual;

export const VISUAL_TYPES: Visual["type"][] = [
  "title", "stat", "comparison", "timeline", "table", "checklist", "alert", "contact",
];

export interface Scene {
  id: string;
  title: string;
  visual: Visual;
  narration: string; // as written: captions and transcript
  speech: string; // rewritten for the ear: text-to-speech
  start_seconds: number;
  duration_seconds: number; // estimated from word count
}

export interface ScenesFile {
  pack: string;
  customer_id: string;
  words_per_second: number;
  total_seconds: number;
  scenes: Scene[];
}
