import { describe, expect, test } from "vitest";
import { contrastRatio, hexToRgb, relativeLuminance } from "./contrast";

describe("contrastRatio", () => {
  test("black on white is the maximum, 21:1", () => {
    expect(contrastRatio("#000000", "#FFFFFF")).toBeCloseTo(21, 5);
  });

  test("a colour on itself is the minimum, 1:1", () => {
    expect(contrastRatio("#0E4D4A", "#0E4D4A")).toBe(1);
  });

  test("#767676 on white is about 4.54, the lightest grey that passes AA", () => {
    expect(contrastRatio("#767676", "#FFFFFF")).toBeCloseTo(4.54, 2);
    expect(contrastRatio("#777777", "#FFFFFF")).toBeLessThan(4.5);
  });

  test("argument order doesn't matter", () => {
    expect(contrastRatio("#FFFFFF", "#1D2424")).toBe(contrastRatio("#1D2424", "#FFFFFF"));
  });
});

describe("relativeLuminance", () => {
  test("runs from 0 for black to 1 for white", () => {
    expect(relativeLuminance("#000000")).toBe(0);
    expect(relativeLuminance("#FFFFFF")).toBeCloseTo(1, 10);
  });
});

describe("hexToRgb", () => {
  test("reads upper or lower case", () => {
    expect(hexToRgb("#0e4d4a")).toEqual([14, 77, 74]);
    expect(hexToRgb("#0E4D4A")).toEqual([14, 77, 74]);
  });

  test.each(["#FFF", "0E4D4A", "#0E4D4G", "", "teal"])("rejects %j", (bad) => {
    expect(() => hexToRgb(bad)).toThrow("Not a 6-digit hex colour");
  });
});
