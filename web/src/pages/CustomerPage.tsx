import { routeHref } from "../routing";
import type { Customer, Pack } from "../types";
import { PageHeading } from "./PageHeading";

/** One customer's explainer. The Player arrives here from 5.7. */
export function CustomerPage({ pack, customer, navigated }: { pack: Pack; customer: Customer; navigated: boolean }) {
  const heading = `${customer.preferred_name}'s explainer`;

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
    </>
  );
}
