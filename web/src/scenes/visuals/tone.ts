import type { Tone } from "../../types";

// A tone is always said in words as well as colour, so colour is never the only signal.
export const TONE_LABEL: Record<Tone, string> = {
  info: "Note",
  important: "Important",
  danger: "Warning",
};
