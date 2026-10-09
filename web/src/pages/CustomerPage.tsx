import { routeHref } from "../routing";
import { SceneVisual } from "../scenes/SceneVisual";
import { useScenes } from "../scenes/useScenes";
import type { Customer, Pack } from "../types";
import { PageHeading } from "./PageHeading";

/** One customer's explainer. For now a storyboard of every scene; the Player takes over in 5.9. */
export function CustomerPage({ pack, customer, navigated }: { pack: Pack; customer: Customer; navigated: boolean }) {
  const heading = `${customer.preferred_name}'s explainer`;
  const scenes = useScenes(pack.name, customer.id);

  return (
    <>
      <p>
        <a className="back-link" href={routeHref(pack.name)}>
          ← All customers
        </a>
      </p>
      <PageHeading documentTitle={`${heading} — ${pack.theme.brand.short_name}`} focusOnMount={navigated}>
        {heading}
      </PageHeading>
      <p className="lead">{customer.persona}</p>

      {scenes.status === "loading" && <p role="status">Loading the explainer…</p>}

      {scenes.status === "error" && (
        <div role="alert" className="load-error">
          <h2>Sorry, this explainer isn't available</h2>
          <p>{scenes.message}</p>
        </div>
      )}

      {scenes.status === "ready" && (
        <ol className="storyboard">
          {scenes.file.scenes.map((scene) => (
            <li key={scene.id} className="storyboard__scene">
              <section aria-labelledby={`scene-${scene.id}`}>
                <h2 id={`scene-${scene.id}`}>{scene.title}</h2>
                <SceneVisual visual={scene.visual} />
                <p className="storyboard__narration">{scene.narration}</p>
              </section>
            </li>
          ))}
        </ol>
      )}
    </>
  );
}
