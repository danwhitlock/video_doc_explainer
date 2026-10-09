import { routeHref } from "../routing";
import { BrandMark } from "../shell/BrandMark";
import type { Pack } from "../types";
import { PageHeading } from "./PageHeading";

/** Choose an industry (re-skins the page), then a customer (opens their explainer). */
export function Home({ pack, packs, navigated }: { pack: Pack; packs: Pack[]; navigated: boolean }) {
  return (
    <>
      <PageHeading
        documentTitle={`Your document, explained — ${pack.theme.brand.short_name}`}
        focusOnMount={navigated}
      >
        Your document, explained
      </PageHeading>
      <p className="lead">
        Choose an industry, then a customer, to see a personalised explainer of their own document.
      </p>

      <nav aria-labelledby="industry-heading">
        <h2 id="industry-heading">Choose an industry</h2>
        <ul className="pack-switcher">
          {packs.map((candidate) => {
            const isCurrent = candidate.name === pack.name;
            return (
              <li key={candidate.name}>
                {/* Links, not buttons: the choice lives in the URL, so Back and bookmarks just work. */}
                <a
                  className="pack-tile"
                  href={routeHref(candidate.name)}
                  aria-current={isCurrent ? "page" : undefined}
                >
                  <BrandMark mark={candidate.theme.brand.mark} name={candidate.theme.brand.name} />
                  <span className="pack-tile__text">
                    <span className="pack-tile__name">{candidate.theme.brand.name}</span>
                    <span className="pack-tile__tagline">{candidate.theme.brand.tagline}</span>
                  </span>
                  {/* Visible text as well as the border, so colour is never the only signal. */}
                  {isCurrent && <span className="pack-tile__current">✓ Showing</span>}
                </a>
              </li>
            );
          })}
        </ul>
      </nav>

      <section aria-labelledby="customers-heading">
        <h2 id="customers-heading">Choose a customer</h2>
        <ul className="customer-cards">
          {pack.customers.map((customer) => (
            <li key={customer.id} className="customer-card">
              <h3 className="customer-card__name">
                {/* The name is the link; CSS stretches its click area over the whole card. */}
                <a className="customer-card__link" href={routeHref(pack.name, customer.id)}>
                  {customer.preferred_name}
                </a>
              </h3>
              <p className="customer-card__persona">{customer.persona}</p>
              <p className="customer-card__cta" aria-hidden="true">
                Watch explainer →
              </p>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
