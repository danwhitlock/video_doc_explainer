import type { Visual } from "../types";

/**
 * Picks the component for a scene's visual type. A switch (rather than a
 * lookup object) lets TypeScript narrow `visual` to the exact shape in each
 * case, so each component gets fully typed fields.
 */
export function SceneVisual({ visual }: { visual: Visual }) {
  switch (visual.type) {
    // Real components replace these placeholders in 5.7b and 5.8.
    case "title":
    case "stat":
    case "comparison":
    case "timeline":
    case "table":
    case "checklist":
    case "alert":
    case "contact":
      return <VisualPlaceholder type={visual.type} />;
    default: {
      // Exhaustiveness check: if a new type is added to Visual but not handled
      // above, `visual` isn't `never` here and the build fails.
      const unhandled: never = visual;
      throw new Error(`Unknown visual type: ${JSON.stringify(unhandled)}`);
    }
  }
}

function VisualPlaceholder({ type }: { type: Visual["type"] }) {
  return <div className="visual-placeholder">{type} visual</div>;
}
