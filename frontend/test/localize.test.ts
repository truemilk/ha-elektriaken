import { describe, expect, it } from "vitest";
import { localize } from "../src/localize";

describe("localize", () => {
  it("falls back to English", () => expect(localize("de", "today")).toBe("Today"));
  it("supports Estonian locales", () => expect(localize("et-EE", "today")).toBe("Täna"));
});

