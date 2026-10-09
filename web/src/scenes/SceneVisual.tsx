import type { Visual } from "../types";
import { AlertVisual } from "./visuals/AlertVisual";
import { ChecklistVisual } from "./visuals/ChecklistVisual";
import { ComparisonVisual } from "./visuals/ComparisonVisual";
import { ContactVisual } from "./visuals/ContactVisual";
import { StatVisual } from "./visuals/StatVisual";
import { TableVisual } from "./visuals/TableVisual";
import { TimelineVisual } from "./visuals/TimelineVisual";
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
    case "comparison":
      return <ComparisonVisual visual={visual} />;
    case "timeline":
      return <TimelineVisual visual={visual} />;
    case "table":
      return <TableVisual visual={visual} />;
    case "checklist":
      return <ChecklistVisual visual={visual} />;
    case "alert":
      return <AlertVisual visual={visual} />;
    case "contact":
      return <ContactVisual visual={visual} />;
    default: {
      // Exhaustiveness check: if a new type is added to Visual but not handled
      // above, `visual` isn't `never` here and the build fails.
      const unhandled: never = visual;
      throw new Error(`Unknown visual type: ${JSON.stringify(unhandled)}`);
    }
  }
}
