import { describe, expect, test } from "vitest";
import { packs } from "./data";
import { parseRoute, routeHref } from "./routing";

const [first, second] = packs;
const customer = second.customers[1];

describe("parseRoute", () => {
  test("a pack name opens that pack's home", () => {
    expect(parseRoute(`#/${second.name}`, packs)).toEqual({ pack: second, customer: null });
  });

  test("a pack and customer opens that customer", () => {
    expect(parseRoute(`#/${second.name}/${customer.id}`, packs)).toEqual({ pack: second, customer });
  });

  test.each(["", "#", "#/", "#/no-such-pack", "#/no-such-pack/m-001"])(
    "%j falls back to the first pack's home",
    (hash) => {
      expect(parseRoute(hash, packs)).toEqual({ pack: first, customer: null });
    },
  );

  test("an unknown customer opens the pack's home", () => {
    expect(parseRoute(`#/${second.name}/x-999`, packs)).toEqual({ pack: second, customer: null });
  });

  test("a customer from a different pack is not accepted", () => {
    const otherPacksCustomer = first.customers[0];
    expect(parseRoute(`#/${second.name}/${otherPacksCustomer.id}`, packs).customer).toBeNull();
  });
});

describe("routeHref", () => {
  test("builds hashes that parseRoute reads back", () => {
    expect(routeHref(second.name)).toBe(`#/${second.name}`);
    expect(parseRoute(routeHref(second.name, customer.id), packs)).toEqual({ pack: second, customer });
  });
});
