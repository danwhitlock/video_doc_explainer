import type { ComparisonVisual as ComparisonData } from "../../types";

type Side = ComparisonData["before"];

function Panel({ side, className }: { side: Side; className: string }) {
  return (
    <div className={`comparison__panel ${className}`}>
      <p className="comparison__label">{side.label}</p>
      <p className="comparison__value">{side.value}</p>
      {side.caption && <p className="comparison__caption">{side.caption}</p>}
    </div>
  );
}

/** Before and after, side by side, with the difference said in words. */
export function ComparisonVisual({ visual }: { visual: ComparisonData }) {
  return (
    <div className="visual visual--comparison">
      <div className="comparison__panels">
        <Panel side={visual.before} className="comparison__panel--before" />
        {/* Decorative: reading order (before, then after) already says this. */}
        <span className="comparison__arrow" aria-hidden="true">
          →
        </span>
        <Panel side={visual.after} className="comparison__panel--after" />
      </div>
      <p className="comparison__delta">{visual.delta}</p>
    </div>
  );
}
