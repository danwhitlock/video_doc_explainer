import type { AlertVisual as AlertData } from "../../types";
import { TONE_LABEL } from "./tone";

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
