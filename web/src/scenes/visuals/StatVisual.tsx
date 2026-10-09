import type { StatVisual as StatData } from "../../types";

/** Key figures, and optionally a meter (e.g. loan to value). */
export function StatVisual({ visual }: { visual: StatData }) {
  const { meter } = visual;
  return (
    <div className="visual visual--stat">
      {/* A description list: screen readers announce each label with its value. */}
      <dl className="stat-list">
        {visual.stats.map((stat) => (
          <div key={stat.label} className="stat-list__item">
            <dt>{stat.label}</dt>
            <dd>{stat.value}</dd>
          </div>
        ))}
      </dl>
      {meter && (
        <div className="stat-meter">
          <p className="stat-meter__label">
            {meter.label} <strong>{`${meter.value}${meter.unit}`}</strong>
          </p>
          {/* Decorative: the value is already written out above. */}
          <div className="stat-meter__track" aria-hidden="true">
            <div
              className="stat-meter__fill"
              style={{ width: `${Math.min(100, (meter.value / meter.max) * 100)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
