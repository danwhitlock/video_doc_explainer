import { routeHref } from "../routing";
import { Player } from "../player/Player";
import { useScenes } from "../scenes/useScenes";
import type { Customer, Pack } from "../types";
import { PageHeading } from "./PageHeading";

/** One customer's explainer: loads their scenes and plays them. */
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
        // key: a different customer gets a fresh player (scene 1, paused),
        // not the previous customer's position.
        <Player
          key={`${pack.name}/${customer.id}`}
          scenes={scenes.file.scenes}
          wordsPerSecond={scenes.file.words_per_second}
          customerRate={customer.prefs.speech_rate}
        />
      )}
    </>
  );
}
