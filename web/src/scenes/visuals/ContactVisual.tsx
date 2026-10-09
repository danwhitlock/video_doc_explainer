import type { ContactVisual as ContactData } from "../../types";

/** "01632 960215" -> "tel:01632960215": phone links need the digits only. */
export function telHref(phone: string): string {
  return `tel:${phone.replace(/[^\d+]/g, "")}`;
}

/** How to get in touch: tappable numbers, the reference to quote, opening hours. */
export function ContactVisual({ visual }: { visual: ContactData }) {
  return (
    <div className="visual visual--contact">
      <dl className="contact-list">
        <div>
          <dt>Call us</dt>
          <dd>
            <a className="contact-list__phone" href={telHref(visual.phone)}>
              {visual.phone}
            </a>
          </dd>
        </div>
        {visual.secondary_phone && (
          <div>
            <dt>Out of hours</dt>
            <dd>
              <a className="contact-list__phone" href={telHref(visual.secondary_phone)}>
                {visual.secondary_phone}
              </a>
            </dd>
          </div>
        )}
        {visual.reference && (
          <div>
            <dt>Your reference</dt>
            <dd className="contact-list__reference">{visual.reference}</dd>
          </div>
        )}
        {visual.hours && (
          <div>
            <dt>Opening hours</dt>
            <dd>{visual.hours}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}
