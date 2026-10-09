import type { TitleVisual as TitleData } from "../../types";

/** Opening panel: the greeting and what the explainer is about. */
export function TitleVisual({ visual }: { visual: TitleData }) {
  return (
    <div className="visual visual--title">
      {/* Styled text, not a heading: the scene's title is already the h2. */}
      <p className="visual--title__heading">{visual.heading}</p>
      {visual.subheading && <p className="visual--title__subheading">{visual.subheading}</p>}
    </div>
  );
}
