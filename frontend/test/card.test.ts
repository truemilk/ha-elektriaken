import { beforeEach, describe, expect, it, vi } from "vitest";
import "../src/elektriaken-card";
import type { ElektriakenCard } from "../src/elektriaken-card";

const response = {
  resolution: 15 as const,
  duration_minutes: 60,
  include_vat: true,
  vat_rate: 24,
  currency: "c/kWh",
  points: [{start: "2025-01-01T00:00:00+00:00", end: "2099-01-01T00:15:00+00:00", price: 5, raw_eur_mwh: 40.3, day: "today" as const}],
  best_window: null,
  tomorrow_available: false,
  updated_at: "2025-01-01T00:00:00+00:00",
};

describe("elektriaken-card", () => {
  let card: ElektriakenCard;
  const sendMessagePromise = vi.fn(async () => response);

  beforeEach(() => {
    sendMessagePromise.mockClear();
    card = document.createElement("elektriaken-card") as ElektriakenCard;
    card.setConfig({type: "custom:elektriaken-card", resolution: 15, duration_minutes: 60});
    card.hass = {language: "en", connection: {sendMessagePromise}} as never;
    document.body.replaceChildren(card);
  });

  it("loads through the authenticated Home Assistant connection", async () => {
    await card.updateComplete;
    await new Promise(resolve => setTimeout(resolve, 0));
    await card.updateComplete;
    expect(sendMessagePromise).toHaveBeenCalledWith(expect.objectContaining({type: "elektriaken/get_prices"}));
    expect(card.shadowRoot?.textContent).toContain("Tomorrow’s prices have not been published yet");
  });

  it("rejects an invalid card type", () => {
    expect(() => card.setConfig({type: "wrong" as never})).toThrow();
  });
});

describe("elektriaken-card-editor", () => {
  it("emits config-changed", async () => {
    const editor = document.createElement("elektriaken-card-editor") as HTMLElement & {setConfig(value: unknown): void; updateComplete: Promise<unknown>};
    editor.setConfig({type: "custom:elektriaken-card"});
    document.body.replaceChildren(editor);
    await editor.updateComplete;
    const listener = vi.fn();
    editor.addEventListener("config-changed", listener);
    editor.shadowRoot?.querySelector("select")?.dispatchEvent(new Event("change", {bubbles: true}));
    expect(listener).toHaveBeenCalledOnce();
  });
});

