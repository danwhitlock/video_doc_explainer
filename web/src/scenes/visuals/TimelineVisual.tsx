import type { TimelineVisual as TimelineData } from "../../types";
import { TONE_LABEL } from "./tone";

/** Steps in time order. An ordered list, because the order is the point. */
export function TimelineVisual({ visual }: { visual: TimelineData }) {
  const tone = visual.tone ?? "info";
  return (
    <div className={`visual visual--timeline visual--tone-${tone}`}>
      {tone !== "info" && <p className="timeline__tone">{TONE_LABEL[tone]}</p>}
      <ol className="timeline">
        {visual.items.map((item) => (
          <li key={`${item.time}-${item.label}`} className="timeline__item">
            <span className="timeline__time">{item.time}</span>
            <span className="timeline__label">{item.label}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
