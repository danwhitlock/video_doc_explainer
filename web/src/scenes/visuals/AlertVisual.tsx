import type { AlertVisual as AlertData, Tone } from "../../types";

// The tone is said in words as well as colour, so colour is never the only signal.
const TONE_LABEL: Record<Tone, string> = {
  info: "Note",
  important: "Important",
  danger: "Warning",
};

/**
 * A callout. Deliberately not role="alert": that makes screen readers
 * interrupt at once, which suits errors, not content you play through.
 */
export function AlertVisual({ visual }: { visual: AlertData }) {
  return (
    <div className={`visual visual--alert visual--alert-${visual.tone}`}>
      <p className="alert__tone">{TONE_LABEL[visual.tone]}</p>
      <p className="alert__heading">{visual.heading}</p>
      {visual.body && <p className="alert__body">{visual.body}</p>}
      {visual.items && (
        <ul className="alert__items">
          {visual.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
