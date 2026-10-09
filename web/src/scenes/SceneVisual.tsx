import type { Visual } from "../types";
import { AlertVisual } from "./visuals/AlertVisual";
import { ContactVisual } from "./visuals/ContactVisual";
import { StatVisual } from "./visuals/StatVisual";
import { TitleVisual } from "./visuals/TitleVisual";

/**
 * Picks the component for a scene's visual type. A switch (rather than a
 * lookup object) lets TypeScript narrow `visual` to the exact shape in each
 * case, so each component gets fully typed fields.
 */
export function SceneVisual({ visual }: { visual: Visual }) {
  switch (visual.type) {
    case "title":
      return <TitleVisual visual={visual} />;
    case "stat":
      return <StatVisual visual={visual} />;
    case "alert":
      return <AlertVisual visual={visual} />;
    case "contact":
      return <ContactVisual visual={visual} />;
    // Real components replace these placeholders in 5.8.
    case "comparison":
    case "timeline":
    case "table":
    case "checklist":
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
