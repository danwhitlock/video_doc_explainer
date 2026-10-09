import type { ChecklistVisual as ChecklistData } from "../../types";

/** Things the customer should do. A plain list, not checkboxes: nothing is saved. */
export function ChecklistVisual({ visual }: { visual: ChecklistData }) {
  return (
    <div className="visual visual--checklist">
      <ul className="checklist">
        {visual.items.map((item) => (
          <li key={item} className="checklist__item">
            <svg className="checklist__tick" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false">
              <circle cx="12" cy="12" r="11" fill="currentColor" />
              <path d="M7 12.5l3.2 3.2L17 9" fill="none" stroke="var(--color-on-primary)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
